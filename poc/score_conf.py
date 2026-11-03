"""EXT (docs/prereg/PREREG_EXT.md): the model's own token confidence in its stored non-thinking answers (N), for the in-model
confidence gate of the cascade literature (Gupta et al. 2024, arXiv 2404.10136). No new samples: each stored answer is
teacher-forced after the exact prompt it was generated from (the server's chat template, thinking off, as llm.chat), and the
log-prob of every answer token and of the end-of-turn token is read from vLLM's prompt_logprobs (raw log-probs).
  sql   = BIRD dev, SQL-1 rows (results/sql/<tag>_cheap_s<s>.jsonl, tags q8b / q14a / q35)
  sqltr = the fresh BIRD-train questions of SQL-PA (tags q8bpa / q14apa / q35pa)
  tc    = BFCL single-turn, TC-1 rows (results/tc/<tag>_cheap_s<s>.jsonl; BFCL's system prompt + the request)
Rows: results/conf/<kind>_<tag>_s<s>.jsonl {id, lp: [answer token log-probs], end: end-of-turn log-prob, rt: the answer re-tokenizes
to the stored token count}. Rows resume.
  rv    = PREREG_LCM addendum RV: channel (reviewer) and direct (coder) scores of the candidate answers in results/conf/rv_req.jsonl
          (written by lcm_shift.py --rv-build), raw text under the plain LM (no chat template), Coder-Reviewer's inverted prompt (Zhang
          et al. 2023): rev = the question / request after the schema or functions and the candidate, cod = the candidate after the
          question. Rows {h, s: summed target log-prob, n: target tokens, pre: prompt tokens} -> results/conf/rv_scores.jsonl
          (RV_SUFFIX=_q35: the peer Qwen3.5-9B's scores, rv_scores_q35.jsonl, addendum RV2)
  sel   = PREREG_LCM addendum SEL: the trained verifier's score of the candidate queries in results/conf/sel_req.jsonl (lcm_shift.py
          --sel-build): each query is run on its database (30 s) and shown as CV-1's turn 2 (cv_train.turn2) under the LoRA adapter
          <name> (the server started with --enable-lora --lora-modules <name>=<dir>); s = logit(ACCEPT) - logit(DE) of the next token from
          the top-20 log-probs (a token outside them gets the 20th's log-prob). Rows {h, s, c: the check, pre: prompt tokens} ->
          results/conf/sel_scores_<name>.jsonl; SEL_SSETS=fresh: only the validation requests
          SEL-PW (SEL_REQ=sel_req_pw.jsonl, kind pw): an ordered pair of queries (text, text2), both run, shown as cv_train.pw_prompt;
          s = logit(A) - logit(B) from the top-20 log-probs, rows -> the same file pattern
usage: POC_BASE_URL=... python score_conf.py <kind> <tag> [seeds ...]   (CONF_LIMIT=k: the first k rows per seed, the smoke)
       POC_BASE_URL=... python score_conf.py rv   (CONF_LIMIT=k: the first k requests)
       POC_BASE_URL=... python score_conf.py sel <name>[,<name> ...]"""
import json, math, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import BASE_URL, client  # noqa: E402
from run_nlopt import _rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
ITEMS = {"sql": f"{PD}/bird/sql_items.jsonl", "sqltr": f"{PD}/bird/sql_train_items.jsonl", "tc": f"{PD}/bfcl/tc_items.jsonl"}
RES = {"sql": "sql", "sqltr": "sql", "tc": "tc"}
TOK = BASE_URL.rsplit("/v1", 1)[0] + "/tokenize"


def tokenize(**kw):
    req = urllib.request.Request(TOK, data=json.dumps({"model": "local", **kw}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["tokens"]


def score(p, row, end_id):
    msgs = ([{"role": "system", "content": p["system"]}] if p.get("system") else []) + [{"role": "user", "content": p["user"]}]
    pre = tokenize(messages=msgs, add_generation_prompt=True, chat_template_kwargs={"enable_thinking": False})
    ans = tokenize(prompt=row["n_text"], add_special_tokens=False)
    ids = pre + ans + [end_id]
    r = client.completions.create(model="local", prompt=ids, max_tokens=1, temperature=0, extra_body={"prompt_logprobs": 0})
    plp = r.choices[0].prompt_logprobs
    lp = []
    for pos in range(len(pre), len(ids)):
        d = plp[pos] or {}
        e = d.get(str(ids[pos]), d.get(ids[pos]))
        lp.append(round(e["logprob"] if isinstance(e, dict) else e.logprob, 4))
    return {"id": row["id"], "lp": lp[:-1], "end": lp[-1], "rt": len(ans) + 1 == row.get("n_tok")}


RV_ITEMS = {("sql", "dev"): f"{PD}/bird/sql_items.jsonl", ("sql", "spider"): f"{PD}/bird/sql_spider_items.jsonl",
            ("sql", "spiderdev"): f"{PD}/bird/sql_spiderdev_items.jsonl", ("tc", "bfcl"): f"{PD}/bfcl/tc_items.jsonl"}
ASK = "Write one SQLite query that answers the question. Return only the query in a ```sql block."


def rv_prompt(task, p, kind, text):
    """(context, target) as raw text. SQL: prep_sql's prompt is <schema>\n\n[-- External knowledge: <ev>\n]-- Question: <q>\n\n<ASK>;
    tool calls: the functions as JSON, the request, the graded calls one per line as name(arg=value, ...)"""
    if task == "sql":
        body = p["user"][:-len(ASK) - 2]
        assert p["user"].endswith("\n\n" + ASK), p["id"]
        i = body.rfind("\n-- Question: ")
        q, pre = body[i + len("\n-- Question: "):], body[:i]
        j = pre.rfind("\n\n-- External knowledge: ")
        schema, ev = (pre[:j], pre[j + len("\n\n-- External knowledge: "):]) if j >= 0 else (pre.rstrip("\n"), None)
        head = schema + "\n\n" + (f"-- External knowledge: {ev}\n" if ev is not None else "")
        if kind == "rev":
            return head + f"-- SQLite query:\n{text}\n-- The question this query answers:", " " + q.strip()
        return head + f"-- Question: {q.strip()}\n-- SQLite query:\n", text
    fn = json.dumps(p["functions"], indent=2)
    if kind == "rev":
        return f"# Available functions\n{fn}\n\n# Function calls made\n{text}\n\n# The user request these calls answer:", " " + p["user"].strip()
    return f"# Available functions\n{fn}\n\n# User request: {p['user'].strip()}\n\n# Function calls made\n", text


def score_rv(row, P):
    ctx, tgt = rv_prompt(row["task"], P[(row["task"], row["sset"])][row["id"]], row["kind"], row["text"])
    a, b = tokenize(prompt=ctx, add_special_tokens=False), tokenize(prompt=tgt, add_special_tokens=False)
    ids = a + b
    r = client.completions.create(model="local", prompt=ids, max_tokens=1, temperature=0, extra_body={"prompt_logprobs": 0})
    plp = r.choices[0].prompt_logprobs
    lp = []
    for pos in range(len(a), len(ids)):
        d = plp[pos] or {}
        e = d.get(str(ids[pos]), d.get(ids[pos]))
        lp.append(e["logprob"] if isinstance(e, dict) else e.logprob)
    return {"h": row["h"], "s": round(sum(lp), 4), "n": len(lp), "pre": len(ids)}


def main_rv():
    P = {k: {p["id"]: p for p in map(json.loads, open(f))} for k, f in RV_ITEMS.items()}
    out = f"{ROOT}/results/conf/rv_scores{os.environ.get('RV_SUFFIX', '')}.jsonl"   # RV2: RV_SUFFIX=_q35 under Qwen3.5-9B
    done = {r["h"] for r in _rows(out)}
    kinds = os.environ.get("RV_KINDS", "rev,cod").split(",")   # RV2: rev only
    rows = [r for r in _rows(f"{ROOT}/results/conf/rv_req.jsonl") if r["h"] not in done and r["kind"] in kinds]
    if os.environ.get("CONF_LIMIT"):
        rows = rows[:int(os.environ["CONF_LIMIT"])]
    n, err = 0, 0
    with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("CONF_POOL", 32))) as ex:
        futs = [ex.submit(score_rv, r, P) for r in rows]
        for fu in futs:
            try:
                f.write(json.dumps(fu.result()) + "\n"); f.flush(); n += 1
            except Exception as e:
                err += 1; print("rv request failed, no row:", repr(e)[:200], flush=True)
            if (n + err) % 1000 == 0:
                print(f"rv: {n + err}/{len(rows)}", flush=True)
    print(f"rv: {n} requests scored, {err} failed", flush=True)
    if err:   # the smoke gates the full run (`smoke && full`): RV2's first server died of OOM in prompt log-probs and every request failed
        sys.exit(1)


SEL_ITEMS = {"dev": f"{PD}/bird/sql_items.jsonl", "spider": f"{PD}/bird/sql_spider_items.jsonl",
             "spiderdev": f"{PD}/bird/sql_spiderdev_items.jsonl", "fresh": f"{PD}/bird/sql_train_items.jsonl"}
SEL_SPLIT = {"dev": "dev", "spider": "spider", "spiderdev": "spiderdev", "fresh": "train"}   # prep_sql's database directories
SEL_ITEMS.update({"bfcl": f"{PD}/bfcl/tc_items.jsonl", "tcho": f"{PD}/toolace/tc_train_items.jsonl",   # SEL-TC: BFCL; held-out ToolACE;
                  "ace": f"{PD}/acebench/tc_items.jsonl",   # addendum ACE: ACEBench
                  "mt": f"{PD}/bfcl/mt_sel_items.jsonl",   # addendum MT-SEL: BFCL multi-turn turn-0 rollouts (mt_peer0.py --sel-build)
                  "mt2": f"{PD}/bfcl/mt_sel2_items.jsonl"})   # addendum MT-SO: turn 0 and the later turns (mt_peer0.py --sel-build2)


def main_sel():
    """SEL (SQL ssets) and SEL-TC (bfcl, tcho: SEL_REQ=sel_req_tc.jsonl; the request, the calls' text, tc_train.TC_ASK; nothing run);
    SEL-PW / SEL-PW-TC (kind pw: text and text2 in one turn, cv_train.pw_prompt / tc_train.tc_pw_prompt; s = logit(A) - logit(B);
    SEL-PW-W: task word, kind pw, the text is the whole pairwise prompt);
    SEL-W (word sets, SEL_REQ=sel_req_w.jsonl: the request's text is VER's whole prompt; s = log P(yes) - log P(no), case variants
    summed, as ver_score.py's p_yes in log-odds)"""
    import prep_sql
    from cv_train import run_query, turn2
    names = sys.argv[2].split(",")
    ssets = os.environ.get("SEL_SSETS", "fresh,dev,spider,spiderdev").split(",")
    req = [r for r in _rows(f"{ROOT}/results/conf/{os.environ.get('SEL_REQ', 'sel_req.jsonl')}") if r["sset"] in ssets]
    P = {k: {p["id"]: p for p in map(json.loads, open(SEL_ITEMS[k]))} for k in ssets if k in SEL_ITEMS}
    for sset in ssets:   # run_query reads prep_sql.SPLIT: one split at a time
        rows = [r for r in req if r["sset"] == sset]
        if sset in SEL_SPLIT:
            prep_sql.SPLIT = SEL_SPLIT[sset]
            qs = sorted({(r["id"], t) for r in rows for t in (r["text"], r.get("text2")) if t is not None})   # SEL-PW: both queries
            with ThreadPoolExecutor(8) as ex:
                rq = dict(zip(qs, ex.map(lambda x: run_query(P[sset][x[0]]["db_id"], x[1], 30.0), qs)))
            bad = [x for x in qs if rq[x][0] != "pass"]   # every candidate passed its 30 s check once: again alone, 120 s
            for x in bad:
                rq[x] = run_query(P[sset][x[0]]["db_id"], x[1], 120.0)
            res = {r["h"]: rq[(r["id"], r["text"])] for r in rows}
            print(f"sel {sset}: {len(qs)} queries run, {sum(v[0] == 'pass' for v in rq.values())} pass ({len(bad)} run again alone)",
                  flush=True)
        else:
            if sset in SEL_ITEMS:
                from tc_train import TC_ASK
            res = {r["h"]: ("pass", None, [], 0, []) for r in rows}
        alias = dict(x.split("=") for x in os.environ.get("SEL_ALIAS", "").split(",") if x)   # e.g. local=localw: another file per job
        for nm in names:
            out = f"{ROOT}/results/conf/sel_scores_{alias.get(nm, nm)}.jsonl"
            done = {r["h"] for r in _rows(out)}

            def one(r):
                c, _, cols, n, first = res[r["h"]]
                if r.get("task") == "word":
                    o = client.chat.completions.create(model=nm, messages=[{"role": "user", "content": r["text"]}], max_tokens=1,
                                                       temperature=0, logprobs=True, top_logprobs=20,
                                                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
                    top = [(t.token, t.logprob) for t in o.choices[0].logprobs.content[0].top_logprobs]
                    lo = min(v for _, v in top)
                    if r.get("kind") == "pw":   # SEL-PW-W: the text is the whole pairwise prompt (ver_build.pw_prompt)
                        tp = dict(top)
                        return {"h": r["h"], "s": round(tp.get("A", lo) - tp.get("B", lo), 4), "c": c, "pre": o.usage.prompt_tokens}
                    lse = lambda w: math.log(sum(math.exp(v) for k, v in top if k.strip().lower() == w) or math.exp(lo))
                    return {"h": r["h"], "s": round(lse("yes") - lse("no"), 4), "c": c, "pre": o.usage.prompt_tokens}
                p = P[sset][r["id"]]
                if r.get("kind") == "pw":
                    if sset in SEL_SPLIT:
                        from cv_train import pw_prompt
                        c2, _, cols2, n2, first2 = rq[(r["id"], r["text2"])]
                        m = [{"role": "user", "content": pw_prompt(p["user"], (r["text"], cols, n, first), (r["text2"], cols2, n2, first2))}]
                    else:   # SEL-PW-TC: the request and both responses in one turn
                        from tc_train import tc_pw_prompt
                        c2 = "pass"
                        m = ([{"role": "system", "content": p["system"]}] if p.get("system") else []) + [
                            {"role": "user", "content": tc_pw_prompt(p["user"], r["text"], r["text2"])}]
                    o = client.chat.completions.create(model=nm, messages=m, max_tokens=1, temperature=0, logprobs=True,
                                                       top_logprobs=20, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
                    top = {t.token: t.logprob for t in o.choices[0].logprobs.content[0].top_logprobs}
                    lo = min(top.values())
                    return {"h": r["h"], "s": round(top.get("A", lo) - top.get("B", lo), 4), "c": [c, c2], "pre": o.usage.prompt_tokens}
                if sset in SEL_SPLIT:
                    m = [{"role": "user", "content": p["user"]}, {"role": "assistant", "content": f"```sql\n{r['text']}\n```"},
                         {"role": "user", "content": turn2(n, cols, first)}]
                else:
                    m = ([{"role": "system", "content": p["system"]}] if p.get("system") else []) + [
                        {"role": "user", "content": p["user"]}, {"role": "assistant", "content": r["text"]}, {"role": "user", "content": TC_ASK}]
                o = client.chat.completions.create(model=nm, messages=m, max_tokens=1, temperature=0, logprobs=True, top_logprobs=20,
                                                   extra_body={"chat_template_kwargs": {"enable_thinking": False}})
                top = {t.token: t.logprob for t in o.choices[0].logprobs.content[0].top_logprobs}
                lo = min(top.values())
                return {"h": r["h"], "s": round(top.get("ACCEPT", lo) - top.get("DE", lo), 4), "c": c, "pre": o.usage.prompt_tokens}
            n, err = 0, 0
            with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("CONF_POOL", 32))) as ex:
                for fu in [ex.submit(one, r) for r in [r for r in rows if r["h"] not in done][:int(os.environ.get("CONF_LIMIT", 10 ** 9))]]:
                    try:
                        f.write(json.dumps(fu.result()) + "\n"); f.flush(); n += 1
                    except Exception as e:
                        err += 1; print("sel request failed, no row:", repr(e)[:200], flush=True)
            print(f"sel {nm} {sset}: {n} scored, {err} failed", flush=True)
            if err:
                sys.exit(1)


def main():
    if sys.argv[1] == "sel":
        return main_sel()
    if sys.argv[1] == "rv":
        return main_rv()
    kind, tag = sys.argv[1], sys.argv[2]
    seeds = [int(x) for x in sys.argv[3:]] or [1, 2, 3]
    P = {p["id"]: p for p in map(json.loads, open(ITEMS[kind]))}
    end = tokenize(prompt="<|im_end|>", add_special_tokens=False)
    assert len(end) == 1, end
    os.makedirs(f"{ROOT}/results/conf", exist_ok=True)
    for s in seeds:
        out = f"{ROOT}/results/conf/{kind}_{tag}_s{s}.jsonl"
        done = {r["id"] for r in _rows(out)}
        rows = [r for r in _rows(f"{ROOT}/results/{RES[kind]}/{tag}_cheap_s{s}.jsonl") if r.get("n_text") and r["id"] in P]
        if os.environ.get("CONF_LIMIT"):
            rows = rows[:int(os.environ["CONF_LIMIT"])]
        rows = [r for r in rows if r["id"] not in done]
        n, rt, lps = 0, 0, []
        with open(out, "a") as f, ThreadPoolExecutor(int(os.environ.get("CONF_POOL", 32))) as ex:
            for o in ex.map(lambda r: score(P[r["id"]], r, end[0]), rows):
                f.write(json.dumps(o) + "\n"); f.flush()
                n += 1; rt += o["rt"]; lps += o["lp"]
                if n % 500 == 0:
                    print(f"{kind} {tag} s{s}: {n}/{len(rows)}", flush=True)
        print(f"{kind} {tag} s{s}: {n} rows scored; re-tokenizes to the stored count {100 * rt / max(1, n):.1f}%; mean token log-prob "
              f"{sum(lps) / max(1, len(lps)):.3f}", flush=True)


if __name__ == "__main__":
    main()
