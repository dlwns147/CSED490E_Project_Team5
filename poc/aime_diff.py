"""PREREG_DIFF addendum AIME (2026-11-23): AIME 2024+2025 (60), where some stored sample is right on 56 and the plurality on 50. For each
problem whose samples (9 sources x 3 seeds) give >= 2 answers, the oracle sees the problem and the two most frequent answers and is asked
which one is right (it may also reject both by giving its own); the returned answer is the oracle's if it equals a candidate, else the
plurality. usage: POC_BASE_URL=... python aime_diff.py run | score"""
import json, os, re, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/results/x1/aime_diff.jsonl"
SRCS = ["q8b_prog", "q8b_text", "q8b_think", "oss20_prog", "oss20_text", "oss20_think", "r1d7_think", "q14a_think", "q32b_think"]
ASK = ("{p}\n\nSeveral solvers disagree. The two most common answers are {a} and {b}. Work through the problem carefully and decide which is "
       "correct (if neither is, give the correct answer). Give only the final integer in \\boxed{{}}.")
num = lambda s: (re.sub(r"[^\d-]", "", str(s or "")) or None)


def pool():
    P = {r["id"]: r["problem"] for v in json.load(open(f"{ROOT}/results/x1/problems.json")).values() for r in v}
    C = defaultdict(Counter); right = defaultdict(set); tok = defaultdict(int)
    for s in SRCS:
        for sd in (1, 2, 3):
            for l in open(f"{ROOT}/results/x1/math_{s}_s{sd}.jsonl"):
                r = json.loads(l)
                if not r["id"].startswith("aime"):
                    continue
                a = num(r.get("boxed") if r.get("mode") != "prog" else (r.get("stdout") or "").strip().splitlines()[-1:] or [""])
                a = num(a[0]) if isinstance(a, list) else a
                tok[r["id"]] += int(r.get("out_tokens") or 0)
                if a:
                    C[r["id"]][a] += 1
                    if str(r["correct"]) == "True":
                        right[r["id"]].add(a)
    return P, C, right, tok


def run():
    from llm import chat
    P, C, right, tok = pool()
    todo = [i for i in C if len(C[i]) >= 2]
    def one(i):
        (a, _), (b, _) = C[i].most_common(2)
        o = chat(ASK.format(p=P[i], a=a, b=b), think=True, max_tokens=30000, temperature=0.7, seed=7)
        m = re.findall(r"\\boxed\{([^{}]*)\}", o.get("text") or "")
        return {"id": i, "a": a, "b": b, "oracle": num(m[-1]) if m else None, "tok": o.get("out_tokens") or 0}
    with ThreadPoolExecutor(32) as ex, open(OUT, "w") as f:
        for r in ex.map(one, todo):
            f.write(json.dumps(r) + "\n"); f.flush()


def score():
    P, C, right, tok = pool()
    O = {json.loads(l)["id"]: json.loads(l) for l in open(OUT)}
    n = len(C); pl = dg = 0
    for i in C:
        p = C[i].most_common(1)[0][0]; pl += p in right[i]
        o = O.get(i); pick = o["oracle"] if o and o["oracle"] in C[i] else p
        dg += pick in right[i]
    print(f"AIME n={n}: plurality {pl}, oracle-resolved {dg}, any sample right {sum(bool(right[i]) for i in C)}; oracle tokens "
          f"{sum(o['tok'] for o in O.values())/n/1000:.1f}k per problem")


if __name__ == "__main__":
    {"run": run, "score": score}[sys.argv[1]]()
