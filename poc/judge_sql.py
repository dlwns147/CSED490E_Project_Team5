"""JUDGE (docs/prereg/PREREG_LCM.md, addendum J): another model as a judge of the quick query, a signal of a different kind than its
own quick answer (verification instead of generation; cf. 2607.06799, LLM judges of text-to-SQL correctness). For every question-seed
whose quick query (N, stored) passes the free check, the served model sees the question (schema, evidence), the query and what running
it returned (row count, columns, first 5 rows, as CV-1's turn 2) and answers yes or no; thinking off, one token, P(yes) from the top
log-probs. Rows: results/sql/judge_<JUDGE_NAME>_<generator tag><suffix>_s<seed>.jsonl {id, p_yes, verdict, in_tokens}.
usage: POC_BASE_URL=... JUDGE_NAME=q35 SQL_SPLIT=<dev|spider> python judge_sql.py <generator tag with suffix, e.g. q8b or q8bsp> [seeds]
SEL-RM (PREREG_LCM.md addendum SEL-RM): --tc-pair <results/conf/rm_req.jsonl> <name> [k/n] — a served ToolRM-Gen judges every pair of
tool-call answers in both orders with its own template (main_tc_pair); --tc-pair-smoke <jsonl of its TRBench prompts>: format check"""
import json, math, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cv_train import RES, post, rows_of, run_query  # noqa: E402
from prep_sql import ASK, ITEMS, extract  # noqa: E402

ASKJ = ("Here is a candidate SQLite query for this question:\n```sql\n{sql}\n```\nRunning it returned {n} row{pl}. The first {k}:\n{cols}\n"
        "{rows}\n\nDoes this query correctly answer the question? Answer with one word, yes or no.")


def judge(p, row, seed):
    sql = extract(row.get("n_text") or "")
    chk, h, cols, n, first = run_query(p["db_id"], sql, 30.0)
    if chk != "pass":
        return {"id": p["id"], "p_yes": None, "verdict": None, "in_tokens": 0}
    rows = "\n".join("\t".join(r)[:300] for r in first)
    msg = p["user"].replace(ASK, "").rstrip() + "\n\n" + ASKJ.format(sql=sql, n=n, pl="" if n == 1 else "s", k=len(first),
                                                                      cols="\t".join(cols)[:300], rows=rows)
    r = post("/v1/chat/completions", {"model": "local", "messages": [{"role": "user", "content": msg}], "max_tokens": 1,
                                       "temperature": 0.0, "logprobs": True, "top_logprobs": 20, "seed": seed,
                                       "chat_template_kwargs": {"enable_thinking": False}})
    top = {t["token"].strip().lower(): t["logprob"] for t in r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]}
    y, no = top.get("yes", -math.inf), top.get("no", -math.inf)
    p_yes = None if y == no == -math.inf else (1.0 / (1.0 + math.exp(no - y)) if y > -math.inf else 0.0)
    return {"id": p["id"], "p_yes": p_yes, "verdict": None if p_yes is None else p_yes >= 0.5, "in_tokens": r["usage"]["prompt_tokens"]}


# addendum SEL-RM (PREREG_LCM.md): ToolRM-Gen (2510.26167) judging pairs of tool-call answers with its own think-mode template
# (TRBench-BFCL's prompt, verbatim, typo included)
RM_HEAD = ("\n<task>\nYou are an expert evaluator of AI assistant performance. Given a complete user-assistant conversation history and two "
           "generated assistant responses, you are to conduct a thorough, fact-based, and comprehensive comparison. Based on specific evidence "
           "from your evaluation, make a clear choice of which response is superior. There may be a list of tools available to the assisatnt. "
           "The assistant starts with one or more cycles of (thinking about which tool to use -> performing tool call -> waiting for tool "
           "response), and ends with (thinking about the answer -> answer of the question). The thinking processes, tool calls, tool "
           "responses, and answer are enclosed within their tags. There could be multiple thinking processes, tool calls, tool call "
           "parameters and tool response parameters.\n</task>\n\n<evaluation_criteria>\n- Available tools must be fully and appropriately "
           "leveraged to meet the requirements.\n- Tool call names must be valid, correct, and complete.\n- Tool call arguments must be valid, "
           "correct, and complete.\n- Fabrication, including the creation of information or knowledge not provided by the user, conflicting "
           "with user input, or not derived from the tools, must be penalized.\n- Repetitive or unnecessary tool calls must be penalized.\n- "
           "Excessive or unnecessary requests for user clarification beyond what is essential must be penalized.\n</evaluation_criteria>\n\n\n")
RM_SYS = ("[system]: # Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function "
          "signatures within <tools></tools> XML tags:\n<tools>\n{tools}\n</tools>\n\nFor each function call, return a json object with "
          "function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{{\"name\": <function-name>, \"arguments\": "
          "<args-json-object>}}\n</tool_call>")
RM_TAIL = ("\n\nOutput your choice (either '1' or '2') within <choice></choice> XML tags. No explanations should precede or follow the "
           "choice. Answer in the following format.\n<choice>\n{your_choice}\n</choice>\n")
RM_NOCALL = "I cannot complete this request with the available functions."   # every no-call answer (fixed in the prereg)
RM_ITEMS = {"tcho": "toolace/tc_train_items.jsonl", "bfcl": "bfcl/tc_items.jsonl", "ace": "acebench/tc_items.jsonl"}
RM_MARK = "Here is a list of functions in json format that you can invoke.\n"


def rm_render(text):
    from tc_reward import decode
    t = (text or "").strip()
    d = decode(t) if t.startswith("[") else None
    if not d:
        return RM_NOCALL
    return "\n".join("<tool_call>\n" + json.dumps({"name": n, "arguments": a}, default=str) + "\n</tool_call>" for n, a in d)


def rm_prompt(p, a, b):
    """the conversation as ToolRM's template has it: the request's functions in the Hermes <tools> block; whatever BFCL's system prompt
    carries after the function list (ACEBench's time and profile) appended to the system turn; the user turn"""
    rest = ""
    if RM_MARK in p["system"]:
        s = p["system"][p["system"].index(RM_MARK) + len(RM_MARK):]
        _, end = json.JSONDecoder().raw_decode(s[s.index("["):])
        rest = s[s.index("[") + end:].strip()
    tools = "\n".join(json.dumps({"type": "function", "function": f}) for f in p["functions"])
    hist = RM_SYS.format(tools=tools) + ("\n\n" + rest if rest else "") + "\n[user]: " + p["user"]
    return (RM_HEAD + "<conversation_history>\n" + hist + "\n</conversation_history>\n\n<current_response_1>\n" + rm_render(a) +
            "\n</current_response_1>\n\n<current_response_2>\n" + rm_render(b) + "\n</current_response_2>" + RM_TAIL)


def rm_judge(msg, seed):
    import re
    try:
        r = post("/v1/chat/completions", {"model": "local", "messages": [{"role": "user", "content": msg}], "max_tokens": 8192,
                                           "temperature": 0.6, "top_p": 0.95, "top_k": 20, "seed": seed})
        c = r["choices"][0]
    except Exception as e:  # noqa: BLE001 (a prompt over the context: no judgment)
        return {"choice": None, "out_tokens": 0, "in_tokens": 0, "finish": f"error {str(e)[:80]}"}
    t = (c["message"].get("content") or "").rsplit("</think>", 1)[-1]
    m = re.search(r"<choice>\s*([12])\s*</choice>", t)
    return {"choice": int(m.group(1)) if m else None, "out_tokens": r["usage"]["completion_tokens"],
            "in_tokens": r["usage"]["prompt_tokens"], "finish": c.get("finish_reason")}


def main_tc_pair():
    """--tc-pair <rm_req.jsonl> <name> [k/n]: every pair, both orders (order 0: a first), shard k of n by request -> results/conf/
    rm_pairs_<name>[_<k>of<n>].jsonl {sset, i, ka, kb, order, choice, win ('a' = ka, 'b' = kb, None), out_tokens, in_tokens, finish}.
    --tc-pair-smoke <trbench jsonl>: ToolRM's own TRBench-BFCL prompts, agreement with their labels (format check)"""
    D = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
    pool = int(os.environ.get("JUDGE_POOL", 64))
    if "--tc-pair-smoke" in sys.argv:
        T = [json.loads(l) for l in open(sys.argv[sys.argv.index("--tc-pair-smoke") + 1])]
        with ThreadPoolExecutor(pool) as ex:
            R = list(ex.map(lambda x: rm_judge(x["prompt"], zlib.crc32(x["uuid"].encode())), T))
        ok = [r["choice"] is not None for r in R]
        print(f"TRBench smoke: {len(R)} prompts, parsed {sum(ok)}, agree with label {sum(str(r['choice']) == x['gt'] for r, x in zip(R, T))}, "
              f"output tokens mean {sum(r['out_tokens'] for r in R) / len(R):.0f} (max {max(r['out_tokens'] for r in R)}), cut "
              f"{sum(r['finish'] == 'length' for r in R)}", flush=True)
        return
    req, name = sys.argv[sys.argv.index("--tc-pair") + 1], sys.argv[sys.argv.index("--tc-pair") + 2]
    sh = sys.argv[sys.argv.index("--tc-pair") + 3] if len(sys.argv) > sys.argv.index("--tc-pair") + 3 else None
    out = f"{os.path.dirname(RES)}/conf/rm_pairs_{name}" + (f"_{sh.replace('/', 'of')}" if sh else "") + ".jsonl"
    items = {s: {p["id"]: p for p in map(json.loads, open(f"{D}/{f}"))} for s, f in RM_ITEMS.items()}
    todo = [json.loads(l) for l in open(req)]
    if sh:
        k, n = map(int, sh.split("/"))
        todo = [x for x in todo if zlib.crc32(f"{x['sset']}|{x['i']}".encode()) % n == k]
    done = {(r["sset"], r["i"], r["ka"], r["kb"], r["order"]) for r in rows_of(out)}
    jobs = [(x, o) for x in todo for o in (0, 1) if (x["sset"], x["i"], x["ka"], x["kb"], o) not in done]
    print(f"tc-pair {name} {sh or ''}: {len(todo)} pairs, {len(jobs)} judgments to run -> {out}", flush=True)

    def one(xo):
        x, o = xo
        a, b = (x["a"], x["b"]) if o == 0 else (x["b"], x["a"])
        r = rm_judge(rm_prompt(items[x["sset"]][x["i"]], a, b), zlib.crc32(f"{x['sset']}|{x['i']}|{x['ka']}|{x['kb']}|{o}".encode()))
        win = None if r["choice"] is None else ("a" if (r["choice"] == 1) == (o == 0) else "b")
        return dict({k: x[k] for k in ("sset", "i", "ka", "kb")}, order=o, win=win, **r)
    with open(out, "a") as f, ThreadPoolExecutor(pool) as ex:
        for k, r in enumerate(ex.map(one, jobs)):
            f.write(json.dumps(r) + "\n"); f.flush()
            if k % 2000 == 1999:
                print(f"  {k + 1} judged", flush=True)
    R = rows_of(out)
    print(f"tc-pair {name} {sh or ''}: {len(R)} rows, unparseable {sum(r['win'] is None for r in R)}, output tokens mean "
          f"{sum(r['out_tokens'] for r in R) / max(1, len(R)):.0f}", flush=True)


def main():
    if "--tc-pair" in sys.argv or "--tc-pair-smoke" in sys.argv:
        return main_tc_pair()
    tag = sys.argv[1]
    seeds = [int(x) for x in sys.argv[2:]] or [1, 2, 3]
    P = {p["id"]: p for p in map(json.loads, open(ITEMS))}
    name = os.environ.get("JUDGE_NAME", "judge")
    for s in seeds:
        out = f"{RES}/judge_{name}_{tag}_s{s}.jsonl"
        done = {r["id"] for r in rows_of(out)}
        todo = [r for r in rows_of(f"{RES}/{tag}_cheap_s{s}.jsonl") if r["id"] in P and r["id"] not in done]
        with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("JUDGE_POOL", 48))) as ex:
            for o in ex.map(lambda r: judge(P[r["id"]], r, s * 1000 + zlib.crc32(r["id"].encode()) % 997), todo):
                f.write(json.dumps(o) + "\n"); f.flush()
        R = rows_of(out)
        v = [r for r in R if r["verdict"] is not None]
        print(f"judge {name} on {tag} s{s}: {len(R)} rows, {len(v)} judged, yes {100 * sum(r['verdict'] for r in v) / max(1, len(v)):.1f}%, "
              f"mean input tokens {sum(r['in_tokens'] for r in v) / max(1, len(v)):.0f}", flush=True)


if __name__ == "__main__":
    main()
