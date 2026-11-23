"""PREREG_DIFF (2026-11-23): resolve disagreeing OEIS programs by asking an oracle model for single terms where they differ.
usage: POC_BASE_URL=... POC_REASONING_EFFORT=medium python oeis_diff.py run <pool>   (pool: all | cheap) -> results/x44/oeis_diff_<pool>.jsonl
       python oeis_diff.py score"""
import glob, json, os, re, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute",
                    "oeis_fresh.json" if os.environ.get("DIFF_FRESH") else "oeis.json")
PFX = "oeisf" if os.environ.get("DIFF_FRESH") else "oeis"   # addendum OEIS-F
ASK = ("Here is an integer sequence.\nName: {name}\nComments: {comments}\nThe sequence starts at index n = {off}.\n\n"
       "Compute the single term a({n}) of this sequence from its definition. Work it out carefully, then give only that integer in \\boxed{{}}.")


def pool(kind):
    C = defaultdict(lambda: defaultdict(list)); tok = defaultdict(int)
    for f in sorted(glob.glob(os.environ.get("DIFF_POOL", f"{ROOT}/results/x44") + f"/{PFX}_*_s*.jsonl")):
        b = os.path.basename(f)
        if "brute" in b or "diff" in b or (kind == "cheap" and "_prog_" not in b):
            continue
        for l in open(f):
            r = json.loads(l); o = r.get("outs"); o = o if isinstance(o, list) else (eval(o) if o else [])
            tok[r["id"]] += int(r.get("out_tokens") or 0)
            if o:
                C[r["id"]]["|".join(map(str, o))].append(str(r["correct"]) == "True")
    return C, tok


def boxed(t):
    m = re.findall(r"\\boxed\{([^{}]*)\}", t or "")
    return re.sub(r"[\s,]", "", m[-1]) if m else None


def run(kind):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from llm import chat
    seqs = {x["id"]: x for x in json.load(open(DATA))}
    C, tok = pool(kind)
    out = f"{ROOT}/results/x44/{PFX}_diff_{kind}{os.environ.get('DIFF_TAG', '')}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()

    def one(i):
        cls = {k: v for k, v in C[i].items()}
        rounds, otok = [], 0
        off = int(str(seqs[i]["offset"]).split(",")[0])
        for _ in range(3):
            if len(cls) < 2:
                break
            terms = {k: k.split("|") for k in cls}
            L = min(len(t) for t in terms.values())
            if os.environ.get("DIFF_SPLIT"):   # v2: the index whose split of the remaining classes (weighted by sample counts) has the most entropy
                import math
                def ent(j):
                    g = defaultdict(int)
                    for k, t in terms.items():
                        g[t[j]] += len(cls[k])
                    tot = sum(g.values())
                    return -sum(v / tot * math.log(v / tot) for v in g.values()) if len(g) > 1 else -1
                j = max(range(L), key=lambda j: (ent(j), -j)) if L else None
                j = j if (j is not None and ent(j) > 0) else None
            else:
                j = next((j for j in range(L) if len({t[j] for t in terms.values()}) > 1), None)
            if j is None:
                break
            q = ASK.format(name=seqs[i]["name"], comments=seqs[i].get("comments", ""), off=off, n=off + j)
            if os.environ.get("DIFF_JUDGE"):   # S*-style baseline (arXiv 2502.14382): the judge sees the candidates' values and picks one
                vals = sorted({t[j] for t in terms.values()})
                q += ("\n\nSeveral programs computed this term and disagree. Their values are: " + ", ".join(vals) +
                      ". Decide which value is correct and give it in \\boxed{}.")
            o = chat(q, think=True, max_tokens=16000, temperature=0.7, seed=1000 + j)
            otok += o.get("out_tokens") or 0; v = boxed(o.get("text"))
            keep = {k: c for k, c in cls.items() if terms[k][j] == v}
            rounds.append({"j": j, "oracle": v, "kept": len(keep), "of": len(cls)})
            if keep:
                cls = keep
            else:
                break
        pick = max(cls, key=lambda k: len(cls[k]))
        return {"id": i, "right": bool(cls[pick][0]), "oracle_tok": otok, "pool_tok": tok[i], "rounds": rounds,
                "plurality_right": bool(C[i][max(C[i], key=lambda k: len(C[i][k]))][0]), "any_right": any(v[0] for v in C[i].values())}

    todo = [i for i in C if i not in done]
    with ThreadPoolExecutor(48) as ex, open(out, "a") as f:
        for r in ex.map(one, todo):
            f.write(json.dumps(r) + "\n"); f.flush()


def score():
    import random
    for kind in ("all", "cheap", "all_q8b", "cheap_q8b", "cheap_split", "cheap_judge"):
        p = f"{ROOT}/results/x44/oeis_diff_{kind}.jsonl"
        if not os.path.exists(p):
            continue
        R = [json.loads(l) for l in open(p)]; n = len(R)
        U = lambda ok, t: 100 * ok - 0.5 * t / 1000
        d = {r["id"]: U(r["right"], r["pool_tok"] + r["oracle_tok"]) - U(r["plurality_right"], r["pool_tok"]) for r in R}
        ids = list(d); rng = random.Random(1); B = 4000
        bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / n for _ in range(B))
        print(f"{kind}: n={n}  DIFF {100*sum(r['right'] for r in R)/n:.1f}%  plurality {100*sum(r['plurality_right'] for r in R)/n:.1f}%  "
              f"any right {100*sum(r['any_right'] for r in R)/n:.1f}%  pool {sum(r['pool_tok'] for r in R)/n/1000:.2f}k  oracle {sum(r['oracle_tok'] for r in R)/n/1000:.2f}k  "
              f"DIFF - vote utility {sum(d.values())/n:+.2f} [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)-1]:+.2f}]")


if __name__ == "__main__":
    run(sys.argv[2]) if sys.argv[1] == "run" else score()
