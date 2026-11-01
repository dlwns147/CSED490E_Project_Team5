"""JUDGE (docs/prereg/PREREG_LCM.md, addendum J): another model as a judge of the quick query, a signal of a different kind than its
own quick answer (verification instead of generation; cf. 2607.06799, LLM judges of text-to-SQL correctness). For every question-seed
whose quick query (N, stored) passes the free check, the served model sees the question (schema, evidence), the query and what running
it returned (row count, columns, first 5 rows, as CV-1's turn 2) and answers yes or no; thinking off, one token, P(yes) from the top
log-probs. Rows: results/sql/judge_<JUDGE_NAME>_<generator tag><suffix>_s<seed>.jsonl {id, p_yes, verdict, in_tokens}.
usage: POC_BASE_URL=... JUDGE_NAME=q35 SQL_SPLIT=<dev|spider> python judge_sql.py <generator tag with suffix, e.g. q8b or q8bsp> [seeds]"""
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


def main():
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
