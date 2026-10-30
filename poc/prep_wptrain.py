"""WP-RL (docs/prereg/PREREG_WPRL.md): training problems from OptMATH-Train (HF Aurora-Gem/OptMATH-Train, 201k synthetic optimization
problems with the optimal objective as "answer"; $POC_DATA/optmath_train/OptMATH-Train.jsonl). The problem text without its gurobipy
note ("# Note:" on) and "# Question:" header; numeric answers only; texts of at most MAXC characters; exact duplicates dropped; and
decontaminated: a problem sharing any lower-cased word 13-gram with any problem of the seven test sets (NL4OPT, IndustryOR, MAMO,
OptMATH-Bench, OptiBench, BWOR, LogiOR: run_nlopt.problems) is dropped. A Random(0) sample of the rest, in that order.
Writes $POC_DATA/optmath_train/wp_train_items.jsonl = {"id", "q", "gold"}.
usage: python prep_wptrain.py [N 8000]"""
import json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import problems  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
MAXC, NG = 4000, 13


def grams(t):
    w = re.findall(r"[a-z0-9]+", t.lower())
    return {" ".join(w[k:k + NG]) for k in range(len(w) - NG + 1)}


def clean(t):
    t = t.split("\n# Note:", 1)[0]
    t = re.sub(r"^\s*#\s*Question:\s*", "", t)
    return t.strip()


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    test = set()
    for which in ("x3", "mamo", "optmath", "optibench", "bwor", "logior"):
        P = problems(which)
        print(which, len(P))
        for p in P:
            test |= grams(p["q"])
    rows, seen, st = [], set(), {"all": 0, "answer": 0, "long": 0, "dup": 0, "contam": 0}
    for k, l in enumerate(open(f"{DATA}/optmath_train/OptMATH-Train.jsonl")):
        st["all"] += 1
        r = json.loads(l)
        try:
            g = float(r["answer"])
        except (TypeError, ValueError):
            st["answer"] += 1; continue
        q = clean(r["input"])
        if len(q) > MAXC:
            st["long"] += 1; continue
        if q in seen:
            st["dup"] += 1; continue
        seen.add(q)
        if grams(q) & test:
            st["contam"] += 1; continue
        rows.append({"id": f"omt-{k}", "q": q, "gold": repr(g)})
    random.Random(0).shuffle(rows)
    with open(f"{DATA}/optmath_train/wp_train_items.jsonl", "w") as f:
        for r in rows[:N]:
            f.write(json.dumps(r) + "\n")
    print(st, "kept", len(rows), "written", min(N, len(rows)))


if __name__ == "__main__":
    main()
