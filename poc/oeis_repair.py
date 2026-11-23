"""PREREG_DIFF addendum OEIS-R (2026-11-23): where the DIFF referee's term matches NO candidate class (a label-free sign that the pool has
no right program), give one repair turn: the definition, the most frequent class's program, and the evidence "a careful computation gives
a(N) = v, your program prints w". The repaired program replaces the DIFF answer if its a(N) equals v (free consistency check).
usage: POC_BASE_URL=... python oeis_repair.py run <orig|fresh>   |   python oeis_repair.py score"""
import glob, json, os, random, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute")
R2 = bool(os.environ.get("OEIS_R2"))   # addendum OEIS-R2: three referee terms as feedback and acceptance test
FIX = ("{task}\n\nHere is a program written for this sequence:\n```python\n{code}\n```\nIt prints {w} for n = {n}, but a careful computation from "
       "the definition gives a({n}) = {v}. Find the mistake in the program and write a corrected program (same input / output format). "
       "Output the final code inside triple backticks.")


def setup(kind):
    pfx = "oeisf" if kind == "fresh" else "oeis"
    seqs = {x["id"]: x for x in json.load(open(f"{DATA}/{'oeis_fresh' if kind == 'fresh' else 'oeis'}.json"))}
    pool = os.environ.get("DIFF_POOL", R)
    code = defaultdict(dict); cnt = defaultdict(lambda: defaultdict(int))
    for f in sorted(glob.glob(f"{pool}/{pfx}_*_prog_s*.jsonl")):
        for l in open(f):
            r = json.loads(l); o = r.get("outs"); o = o if isinstance(o, list) else (eval(o) if o else [])
            if o and r.get("code"):
                k = "|".join(map(str, o)); cnt[r["id"]][k] += 1; code[r["id"]].setdefault(k, r["code"])
    D = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{pfx}_diff_cheap_split.jsonl")}
    return pfx, seqs, code, cnt, D


def run(kind):
    from llm import chat, last_block
    import run_compute as RC
    pfx, seqs, code, cnt, D = setup(kind)
    out = f"{R}/{pfx}_repair{'2' if R2 else ''}.jsonl"
    todo = []
    for i, d in D.items():
        miss = [x for x in d["rounds"] if x["kept"] == 0 and x["oracle"] is not None]
        if not miss or not cnt[i]:
            continue
        k = max(cnt[i], key=cnt[i].get); x = miss[0]; j = x["j"]; terms = k.split("|")
        if j >= len(terms):
            continue
        todo.append((i, k, j, x["oracle"], terms[j]))

    ASK1 = ("Here is an integer sequence.\nName: {name}\nComments: {comments}\nThe sequence starts at index n = {off}.\n\n"
            "Compute the single term a({n}) of this sequence from its definition. Work it out carefully, then give only that integer in \\boxed{{}}.")
    import re, math

    def extra_terms(i, j, off):
        """R2: two more referee terms at the most-disputed indices other than j (entropy of the candidates' values, sample-weighted)"""
        ks = list(cnt[i]); T = {k: k.split("|") for k in ks}; L = min(len(t) for t in T.values())
        def ent(x):
            g = defaultdict(int)
            for k in ks:
                g[T[k][x]] += cnt[i][k]
            tot = sum(g.values()); return -sum(v / tot * math.log(v / tot) for v in g.values())
        idx = sorted((x for x in range(L) if x != j), key=lambda x: (-ent(x), x))[:2]
        got, tok = [], 0
        for x in idx:
            o = chat(ASK1.format(name=seqs[i]["name"], comments=seqs[i].get("comments", ""), off=off, n=off + x), think=True, max_tokens=16000,
                     temperature=0.7, seed=1000 + x)
            tok += o.get("out_tokens") or 0
            m = re.findall(r"\\boxed\{([^{}]*)\}", o.get("text") or "")
            if m:
                got.append((x, re.sub(r"[\s,]", "", m[-1])))
        return got, tok

    def one(t):
        i, k, j, v, w = t
        off = int(str(seqs[i]["offset"]).split(",")[0])
        task = RC.OEIS.format(name=seqs[i]["name"], comments=seqs[i].get("comments", ""))
        pts, xtok = [(j, str(v))], 0
        if R2:
            more, xtok = extra_terms(i, j, off); pts += more
        ev = "; ".join(f"a({off + x}) = {val}" for x, val in pts)
        prog = k.split("|")
        fix = FIX.format(task=task, code=code[i][k].strip(), w=w, n=off + j, v=v) if not R2 else (
            f"{task}\n\nHere is a program written for this sequence:\n```python\n{code[i][k].strip()}\n```\nIt prints "
            + ", ".join(f"{prog[x] if x < len(prog) else '?'} for n = {off + x}" for x, _ in pts)
            + f", but careful computations from the definition give {ev}. Find the mistake and write a corrected program (same input / "
              "output format). Output the final code inside triple backticks.")
        o = chat(fix, think=True, max_tokens=16000, temperature=0.7, seed=11)
        c = last_block(o.get("text") or "", ("python", "py", "python3", ""))
        ok, right, outs = RC.run_seq(c, seqs[i]["offset"], seqs[i]["terms"], k=RC.NTERMS) if c else (False, 0, [])
        consistent = bool(outs) and all(x < len(outs) and str(outs[x]).strip() == val for x, val in pts)
        return {"id": i, "j": j, "oracle": v, "pts": pts, "tok": (o.get("out_tokens") or 0) + xtok, "correct": bool(ok), "consistent": consistent}
    with ThreadPoolExecutor(32) as ex, open(out, "w") as f:
        for z in ex.map(one, todo):
            f.write(json.dumps(z) + "\n"); f.flush()


def score():
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    for kind in ("orig", "fresh"):
        pfx, seqs, code, cnt, D = setup(kind)
        p = f"{R}/{pfx}_repair{'2' if R2 else ''}.jsonl"
        if not os.path.exists(p):
            continue
        Z = {json.loads(l)["id"]: json.loads(l) for l in open(p)}
        base = {i: U(d["right"], d["pool_tok"] + d["oracle_tok"]) for i, d in D.items()}
        new = {}
        for i, d in D.items():
            z = Z.get(i); t = d["pool_tok"] + d["oracle_tok"]
            new[i] = U(z["correct"], t + z["tok"]) if (z and z["consistent"]) else U(d["right"], t + (z["tok"] if z else 0))
        ids = sorted(D); dd = {i: new[i] - base[i] for i in ids}; rng = random.Random(1); B = 4000
        bs = sorted(sum(dd[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B))
        acc0 = sum(D[i]["right"] for i in ids) / len(ids)
        acc1 = sum((Z[i]["correct"] if (i in Z and Z[i]["consistent"]) else D[i]["right"]) for i in ids) / len(ids)
        print(f"{kind}: repaired {len(Z)} (consistent {sum(z['consistent'] for z in Z.values())}, right {sum(z['correct'] for z in Z.values())}); "
              f"accuracy {100*acc0:.1f}% -> {100*acc1:.1f}%; utility diff {sum(dd.values())/len(ids):+.2f} [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)-1]:+.2f}] "
              f"p={(sum(x<=0 for x in bs)+1)/(B+1):.4f}")


if __name__ == "__main__":
    run(sys.argv[2]) if sys.argv[1] == "run" else score()
