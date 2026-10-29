"""CV-1 (docs/prereg/PREREG_CV.md): a trained quick mode on BIRD dev, as SQL-1's cheap arm (same questions, per-question seeds,
sampling T 0.7, 2k cap, 30 s check), plus turn 2 where the query passes the check: P(ACCEPT) against DEFER's first token from the
server's top log-probs (greedy: ACCEPT if larger). Rows go to results/sql/<tag>_cheap_s<seed>.jsonl in the cheap arm's format (graded by
grade_sql.py as N) with g_acc (P(ACCEPT) over the two; None where turn 2 was not asked) and dfr (turn 1 replied DEFER).
c2: turn 1 is SQL-1's base query (q8b's cheap rows of that seed), only turn 2 runs; c1: no turn 2.
usage: python cv_eval.py <cv|c1|c2> <tag> <adapter dir> <seed>   (POC_BASE_URL: a server started with --enable-lora)"""
import json, math, os, sys, urllib.error, urllib.request, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ["SQL_SPLIT"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cv_train import BASE_URL, RES, is_defer, post, prompt1, rows_of, run_query, turn2  # noqa: E402
from prep_sql import ITEMS, extract  # noqa: E402


def gate(model, msgs):
    r = post("/v1/chat/completions", {"model": model, "messages": msgs, "max_tokens": 1, "temperature": 0.0, "logprobs": True,
                                      "top_logprobs": 20, "chat_template_kwargs": {"enable_thinking": False}})
    top = {t["token"]: t["logprob"] for t in r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]}
    a, d = top.get("ACCEPT", -math.inf), top.get("DE", -math.inf)
    if a == d == -math.inf:
        return None
    return 1.0 / (1.0 + math.exp(d - a)) if a > -math.inf else 0.0


def main():
    arm, tag, adapter, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    try:
        post("/v1/load_lora_adapter", {"lora_name": "eval", "lora_path": os.path.abspath(adapter)})
    except urllib.error.HTTPError as e:   # seeds 2-3 of one lane: the adapter is already loaded on this server
        with urllib.request.urlopen(BASE_URL + "/models", timeout=60) as r:
            if e.code != 400 or "eval" not in {m["id"] for m in json.load(r)["data"]}:
                raise
    P = [json.loads(l) for l in open(ITEMS)]
    if os.environ.get("SQL_SUBSET"):   # the smoke
        i, k = map(int, os.environ["SQL_SUBSET"].split("/")); P = P[i::k]
    base = {r["id"]: r for r in rows_of(f"{RES}/q8b_cheap_s{seed}.jsonl")} if arm == "c2" else {}
    path = f"{RES}/{tag}_cheap_s{seed}.jsonl"
    done = {r["id"] for r in rows_of(path)}
    sd = lambda p: seed * 1000 + zlib.crc32(p["id"].encode()) % 997

    def one(p):
        m1 = [{"role": "user", "content": prompt1(p["user"], arm)}]
        if arm == "c2":
            b = base[p["id"]]
            text, ntok, fin = b["n_text"], b["n_tok"], b["n_finish"]
        else:
            r = post("/v1/chat/completions", {"model": "eval", "messages": m1, "temperature": 0.7, "top_p": 0.95, "max_tokens": 2048,
                                              "seed": sd(p), "chat_template_kwargs": {"enable_thinking": False}})
            text, ntok, fin = r["choices"][0]["message"]["content"] or "", r["usage"]["completion_tokens"], r["choices"][0]["finish_reason"]
        dfr = arm == "cv" and is_defer(text)
        c, _, cols, n, first = run_query(p["db_id"], extract(text), 30.0) if not dfr else ("defer", None, [], 0, [])
        g = None
        if c == "pass" and arm != "c1":
            g = gate("eval", m1 + [{"role": "assistant", "content": text}, {"role": "user", "content": turn2(n, cols, first)}])
        return {"id": p["id"], "n_text": text, "n_tok": ntok, "n_finish": fin, "c_n": c, "g_acc": g, "dfr": dfr, "s_ans": "", "s_tok": 0}

    with open(path, "a") as f, ThreadPoolExecutor(32) as ex:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done and (arm != "c2" or p["id"] in base)]):
            try:
                f.write(json.dumps(fu.result()) + "\n"); f.flush()
            except Exception as e:
                print(tag, seed, "request failed, no row:", repr(e)[:200], flush=True)
    print(tag, seed, len(rows_of(path)), "rows", flush=True)


if __name__ == "__main__":
    main()
