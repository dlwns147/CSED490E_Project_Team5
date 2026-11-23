"""PREREG_DIFF addendum OEIS-B (2026-11-23): the MC-R lesson on OEIS. A cheap program whose first 8 terms disagree with the same model's
own brute force (or that prints nothing) gets ONE repair turn with that evidence (term by term: program vs brute force); the repaired
program replaces the original if its first 8 terms now equal the brute force's. Compared with the program alone (same seed).
Source: gpt-oss-120b prog + brute, seeds 1-2, the original 500 sequences (the fresh set has no brute-force rows).
usage: POC_BASE_URL=... python oeis_brute_repair.py run <seed> | score"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute", "oeis.json")
FIX = ("{task}\n\nHere is your program for this sequence:\n```python\n{code}\n```\nA separate brute-force program written straight from the definition "
       "disagrees with it on the first terms:\n{diff}\nFind which one follows the definition, fix the program if it is wrong, and output the final "
       "code inside triple backticks.")
L = lambda v: [str(x) for x in (v if isinstance(v, list) else (eval(v) if v else []))]


def pairs(seed):
    P = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/oeis_oss120_prog_s{seed}.jsonl")}
    B = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/oeis_oss120_brute_s{seed}.jsonl")}
    return P, B


def run(seed):
    from llm import chat, last_block
    import run_compute as RC
    seqs = {x["id"]: x for x in json.load(open(DATA))}
    P, B = pairs(seed)
    todo = []
    for i, p in P.items():
        b = L(B.get(i, {}).get("outs")); o = L(p.get("outs"))
        if len(b) == 8 and p.get("code") and o[:8] != b:
            todo.append(i)

    def one(i):
        p, b = P[i], L(B[i]["outs"]); o = L(p.get("outs")); off = int(str(seqs[i]["offset"]).split(",")[0])
        diff = "\n".join(f"n = {off + k}: program {o[k] if k < len(o) else 'nothing'}, brute force {b[k]}" for k in range(8))
        task = RC.OEIS.format(name=seqs[i]["name"], comments=seqs[i].get("comments", ""))
        r = chat(FIX.format(task=task, code=p["code"].strip(), diff=diff), think=True, max_tokens=16000, temperature=0.7, seed=seed * 100 + 7)
        c = last_block(r.get("text") or "", ("python", "py", "python3", ""))
        ok, right, outs = RC.run_seq(c, seqs[i]["offset"], seqs[i]["terms"], k=RC.NTERMS) if c else (False, 0, [])
        return {"id": i, "tok": r.get("out_tokens") or 0, "correct": bool(ok), "consistent": [str(x) for x in outs[:8]] == b}
    with ThreadPoolExecutor(32) as ex, open(f"{R}/oeis_oss120_brR_s{seed}.jsonl", "w") as f:
        for z in ex.map(one, todo):
            f.write(json.dumps(z) + "\n"); f.flush()


def score():
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    base, rep = {}, {}
    for s in (1, 2):   # gpt-oss-120b prog exists for seeds 1-2
        P, B = pairs(s)
        pp = f"{R}/oeis_oss120_brR_s{s}.jsonl"
        Z = {json.loads(l)["id"]: json.loads(l) for l in open(pp)} if os.path.exists(pp) else {}
        for i, p in P.items():
            t = int(p.get("out_tokens") or 0); tb = int(B.get(i, {}).get("out_tokens") or 0); ok = str(p["correct"]) == "True"
            base.setdefault(i, []).append(U(ok, t))
            z = Z.get(i)
            rep.setdefault(i, []).append(U(z["correct"] if (z and z["consistent"]) else ok, t + tb + (z["tok"] if z else 0)))
    ids = sorted(base); d = {i: sum(rep[i]) / len(rep[i]) - sum(base[i]) / len(base[i]) for i in ids}
    rng = random.Random(1); B_ = 4000
    bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B_))
    print(f"program alone U {sum(sum(base[i])/len(base[i]) for i in ids)/len(ids):.2f}  + brute check + repair U {sum(sum(rep[i])/len(rep[i]) for i in ids)/len(ids):.2f}  "
          f"diff {sum(d.values())/len(ids):+.2f} [{bs[int(.025*B_)]:+.2f}, {bs[int(.975*B_)-1]:+.2f}] p={(sum(x<=0 for x in bs)+1)/(B_+1):.4f}")


if __name__ == "__main__":
    run(int(sys.argv[2])) if sys.argv[1] == "run" else score()
