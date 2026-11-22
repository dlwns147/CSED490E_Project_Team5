"""PREREG_VOI amendment 5 (2026-11-22, OEIS development): a label-free reviewer score for each distinct candidate program of an OEIS
sequence — Coder-Reviewer reranking's channel direction (Zhang et al. 2023): log p(the sequence's name | the program), summed over the
name's tokens, under the plain LM (no chat template). One score per (sequence, answer class); the class's first stored program is shown.
Candidates: the prog / think rows of Qwen3-8B, gpt-oss-20b and gpt-oss-120b, seeds 1-3, that printed terms (the VOI pool).
usage: POC_BASE_URL=... python score_oeis_rev.py   -> results/conf/oeis_rev_scores.jsonl {id, key, s, n}"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import client  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute", "oeis.json")
OUT = f"{ROOT}/results/conf/oeis_rev_scores.jsonl"
FILES = [("q8b", "prog", "oeis_q8b_prog_s{s}"), ("q8b", "think", None), ("oss20", "prog", "oeis_oss20_prog_s{s}"),
         ("oss20", "think", "oeis_oss20M_think_s{s}"), ("oss120", "prog", "oeis_oss120_prog_s{s}"), ("oss120", "think", "oeis_oss120_think_s{s}")]


def rows(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def tok(text):
    import urllib.request
    base = os.environ["POC_BASE_URL"].rsplit("/v1", 1)[0]
    req = urllib.request.Request(f"{base}/tokenize", data=json.dumps({"model": "local", "prompt": text, "add_special_tokens": False}).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=600).read())["tokens"]


def main():
    seqs = {x["id"]: x for x in json.load(open(DATA))}
    cand = {}
    for m, mode, pat in FILES:
        for s in (1, 2, 3):
            fn = f"{ROOT}/results/x44/" + (pat.format(s=s) if pat else f"oeis_{'q8bT' if s == 1 else 'q8bTg'}_think_s{s}") + ".jsonl"
            for r in rows(fn):
                outs = r.get("outs"); outs = outs if isinstance(outs, list) else (eval(outs) if outs else [])
                if outs and r.get("code"):
                    key = "|".join(map(str, outs))
                    cand.setdefault((r["id"], key), r["code"])
    done = {(r["id"], r["key"]) for r in rows(OUT)}
    todo = [(i, k, c) for (i, k), c in cand.items() if (i, k) not in done and i in seqs]
    if os.environ.get("CONF_LIMIT"):
        todo = todo[:int(os.environ["CONF_LIMIT"])]
    print(len(cand), "candidates,", len(todo), "to score", flush=True)

    def one(t):
        i, k, code = t
        ctx = f"# Python program\n{code.strip()[:6000]}\n\n# The OEIS sequence whose n-th term this program prints is named:"
        tgt = " " + seqs[i]["name"].strip()
        a, b = tok(ctx), tok(tgt)
        r = client.completions.create(model="local", prompt=a + b, max_tokens=1, temperature=0, extra_body={"prompt_logprobs": 0})
        plp = r.choices[0].prompt_logprobs
        lp = []
        for pos in range(len(a), len(a) + len(b)):
            d = plp[pos] or {}
            e = d.get(str((a + b)[pos]), d.get((a + b)[pos]))
            lp.append(e["logprob"] if isinstance(e, dict) else e.logprob)
        return {"id": i, "key": k, "s": round(sum(lp), 4), "n": len(lp)}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n = err = 0
    with open(OUT, "a") as f, ThreadPoolExecutor(32) as ex:
        for fu in [ex.submit(one, t) for t in todo]:
            try:
                f.write(json.dumps(fu.result()) + "\n"); f.flush(); n += 1
            except Exception as e:
                err += 1; print("failed:", repr(e)[:200], flush=True)
    print(f"scored {n}, failed {err}", flush=True)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
