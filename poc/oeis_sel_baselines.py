"""PREREG_DIFF addendum SELB (2026-11-24): recent program-selection methods as baselines for DIFF on OEIS, same pool, same oracle.
- EXPAIRT (ExPairT-LLM, Yuviler & Drachsler-Cohen, AAAI 2026, arXiv 2511.10855): cluster the candidates by their outputs on the inputs
  I (here the first 10 indices), then a round-robin of pairwise MEMBERSHIP queries — "which output list is more suitable for the task
  and inputs?" — and Copeland scoring; the top cluster is returned. The equivalence-query refinement is not run (the clusters are already
  defined by full outputs, and its ablation costs 7.7 points on HumanEval in the paper; stated as a deviation).
- SSTAR (S*, EMNLP Findings 2025): pairwise adaptive selection with a distinguishing input — for each match the input where the two
  candidates' outputs differ is taken (here: the first index where the two sequences differ, found by execution, which is what S*'s
  generated input is for), both outputs at that input are shown, and the oracle picks; a knockout over the clusters (largest first).
Oracle: gpt-oss-120b medium, as DIFF. usage: POC_BASE_URL=... python oeis_sel_baselines.py run <expairt|sstar> [fresh]   | score [fresh]"""
import glob, json, os, random, re, sys, zlib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
FRESH = "fresh" in sys.argv[2:]
PFX = "oeisf" if FRESH else "oeis"
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute", "oeis_fresh.json" if FRESH else "oeis.json")
K = 10
MEM = ("Here is an integer sequence.\nName: {name}\nComments: {comments}\nThe sequence starts at index n = {off}.\n\n"
       "Two candidate programs print these values for n = {ns}:\nList 1: {a}\nList 2: {b}\n\n"
       "Which output list is correct for this sequence? Check the definition carefully. End with \\boxed{{1}} or \\boxed{{2}}.")
PAIR = ("Here is an integer sequence.\nName: {name}\nComments: {comments}\nThe sequence starts at index n = {off}.\n\n"
        "Two candidate programs disagree at n = {n}: one prints {a}, the other prints {b}.\nWhich value is a({n})? Check the definition "
        "carefully. End with \\boxed{{1}} for {a} or \\boxed{{2}} for {b}.")
L = lambda v: [str(x) for x in (v if isinstance(v, list) else (eval(v) if v else []))]


def pool():
    C = defaultdict(lambda: defaultdict(list)); tok = defaultdict(int)
    for f in sorted(glob.glob(f"{R}/{PFX}_*_prog_s*.jsonl")):
        if "q36" in os.path.basename(f):
            continue   # DIFF v2's pool: three families x 3 seeds
        for l in open(f):
            r = json.loads(l); tok[r["id"]] += int(r.get("out_tokens") or 0); o = L(r.get("outs"))
            if o:
                C[r["id"]]["|".join(o)].append(str(r["correct"]) == "True")
    return C, tok


def pick(t):
    m = re.findall(r"\\boxed\{\s*([12])\s*\}", t or "")
    return int(m[-1]) if m else None


def run(meth):
    from llm import chat
    seqs = {x["id"]: x for x in json.load(open(DATA))}
    C, tok = pool()
    out = f"{R}/{PFX}_selb_{meth}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()

    def one(i):
        s = seqs[i]; off = int(str(s["offset"]).split(",")[0])
        cls = sorted(C[i].items(), key=lambda kv: -len(kv[1]))
        res = {"id": i, "calls": 0, "tok": 0}
        if len(cls) < 2:
            res["right"] = bool(cls and cls[0][1][0]); return res
        if meth == "expairt":
            # clusters on the inputs I = first K indices (classes that agree there merge; the merged cluster answers by its largest class)
            G = defaultdict(list)
            for k, v in cls:
                G["|".join(k.split("|")[:K])].append((k, v))
            keys = list(G)
            if len(keys) == 1:
                best = max(G[keys[0]], key=lambda kv: len(kv[1])); res["right"] = bool(best[1][0]); return res
            score = defaultdict(int)
            for a in range(len(keys)):
                for b in range(a + 1, len(keys)):
                    A, B = keys[a].split("|"), keys[b].split("|")
                    o = chat(MEM.format(name=s["name"], comments=s.get("comments", ""), off=off, ns=", ".join(str(off + x) for x in range(min(len(A), len(B)))),
                                        a=", ".join(A), b=", ".join(B)), think=True, max_tokens=16000, temperature=0.7,
                             seed=7000 + zlib.crc32(f"{i}|{a}|{b}".encode()) % 997)
                    res["calls"] += 1; res["tok"] += o.get("out_tokens") or 0
                    w = pick(o.get("text")); score[keys[a] if w != 2 else keys[b]] += 1
            top = max(keys, key=lambda k: (score[k], sum(len(v) for _, v in G[k])))
            best = max(G[top], key=lambda kv: len(kv[1])); res["right"] = bool(best[1][0])
        else:   # sstar: knockout, largest classes first, one distinguishing index per match
            alive = cls[:]
            while len(alive) > 1:
                nxt = []
                for a in range(0, len(alive) - 1, 2):
                    (ka, va), (kb, vb) = alive[a], alive[a + 1]
                    A, B = ka.split("|"), kb.split("|")
                    j = next((x for x in range(min(len(A), len(B))) if A[x] != B[x]), None)
                    if j is None:
                        nxt.append(alive[a] if len(va) >= len(vb) else alive[a + 1]); continue
                    o = chat(PAIR.format(name=s["name"], comments=s.get("comments", ""), off=off, n=off + j, a=A[j], b=B[j]), think=True,
                             max_tokens=16000, temperature=0.7, seed=8000 + zlib.crc32(f"{i}|{ka[:40]}|{kb[:40]}".encode()) % 997)
                    res["calls"] += 1; res["tok"] += o.get("out_tokens") or 0
                    nxt.append(alive[a + 1] if pick(o.get("text")) == 2 else alive[a])
                if len(alive) % 2:
                    nxt.append(alive[-1])
                alive = nxt
            res["right"] = bool(alive[0][1][0])
        return res
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for z in ex.map(one, [i for i in C if i not in done]):
            f.write(json.dumps(z) + "\n"); f.flush()


def score():
    C, tok = pool()
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    D = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{PFX}_diff_cheap_split.jsonl")}
    A = {"DIFF v2": {i: (d["right"], d["pool_tok"] + d["oracle_tok"], None) for i, d in D.items()}}
    for m in ("expairt", "sstar"):
        p = f"{R}/{PFX}_selb_{m}.jsonl"
        if os.path.exists(p):
            Z = {json.loads(l)["id"]: json.loads(l) for l in open(p)}
            A[m] = {i: (Z[i]["right"], tok[i] + Z[i]["tok"], Z[i]["calls"]) if i in Z else (False, tok[i], 0) for i in D}
    ids = sorted(D)
    for m, v in A.items():
        calls = [c for _, _, c in v.values() if c is not None]
        print(f"{PFX} {m:8s} accuracy {100*sum(v[i][0] for i in ids)/len(ids):.1f}%  tokens {sum(v[i][1] for i in ids)/len(ids):.0f}  "
              f"utility {sum(U(*v[i][:2]) for i in ids)/len(ids):.2f}" + (f"  oracle calls/seq {sum(calls)/len(calls):.2f}" if calls else ""))
    for m in A:
        if m == "DIFF v2":
            continue
        d = [U(*A["DIFF v2"][i][:2]) - U(*A[m][i][:2]) for i in ids]; rng = random.Random(1)
        bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
        print(f"{PFX} DIFF v2 - {m}: {sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}]")


if __name__ == "__main__":
    run(sys.argv[2]) if sys.argv[1] == "run" else score()
