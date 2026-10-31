"""EXT (docs/prereg/PREREG_EXT.md): the model's own token confidence in its stored non-thinking answers (N), for the in-model
confidence gate of the cascade literature (Gupta et al. 2024, arXiv 2404.10136). No new samples: each stored answer is
teacher-forced after the exact prompt it was generated from (the server's chat template, thinking off, as llm.chat), and the
log-prob of every answer token and of the end-of-turn token is read from vLLM's prompt_logprobs (raw log-probs).
  sql   = BIRD dev, SQL-1 rows (results/sql/<tag>_cheap_s<s>.jsonl, tags q8b / q14a / q35)
  sqltr = the fresh BIRD-train questions of SQL-PA (tags q8bpa / q14apa / q35pa)
  tc    = BFCL single-turn, TC-1 rows (results/tc/<tag>_cheap_s<s>.jsonl; BFCL's system prompt + the request)
Rows: results/conf/<kind>_<tag>_s<s>.jsonl {id, lp: [answer token log-probs], end: end-of-turn log-prob, rt: the answer re-tokenizes
to the stored token count}. Rows resume.
usage: POC_BASE_URL=... python score_conf.py <kind> <tag> [seeds ...]   (CONF_LIMIT=k: the first k rows per seed, the smoke)"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import BASE_URL, client  # noqa: E402
from run_nlopt import _rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
ITEMS = {"sql": f"{PD}/bird/sql_items.jsonl", "sqltr": f"{PD}/bird/sql_train_items.jsonl", "tc": f"{PD}/bfcl/tc_items.jsonl"}
RES = {"sql": "sql", "sqltr": "sql", "tc": "tc"}
TOK = BASE_URL.rsplit("/v1", 1)[0] + "/tokenize"


def tokenize(**kw):
    r = httpx.post(TOK, json={"model": "local", **kw}, timeout=600)
    r.raise_for_status()
    return r.json()["tokens"]


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


def main():
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
