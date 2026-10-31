"""MT (docs/prereg/PREREG_MT.md): arms N / E / F / T of run_mt.py, graded by grade_mt.py. Per model: the items every arm has at
every seed; per item the seed means of right and of output tokens (every step); utility = right - 0.5 x ktokens (points). Paired 95%
intervals over items (analyze_ho3.ci). MT-P1 T - N accuracy; MT-P2 E - T utility; MT-P3 E - N utility; MT-P4 F - E utility (each
lower bound > 0, decided per model, a prediction needs 2 of 3). MT-P5: of N's wrong item-seeds the share whose trajectory shows a
visible failure (a call error or a no-progress repeat) >= 50%, and E - N accuracy on N's visible item-seeds > on N's silent ones (point
estimates; the difference reported with a bootstrap interval over items). Reported: per category, BFCL error types, think steps,
N's strata RV / RS / WV / WS (right / wrong x visible / silent) with E's and T's accuracy in each, loops, T - E on N's silent items.
usage: python analyze_mt.py [tag ...]   (default q14a q35 q8b; MT_SEEDS=1,2,3)"""
import json, os, random, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
ARMS, LAM = "NEFT", 0.5
SEEDS = [int(x) for x in os.environ.get("MT_SEEDS", "1,2,3").split(",")]


def load(tag, a, s):
    f, g = f"{RES}/mt_{tag}_{a}_s{s}.jsonl", f"{RES}/mt_grades_{tag}_{a}_s{s}.json"
    if not (os.path.exists(f) and os.path.exists(g)):
        return None
    G = json.load(open(g))
    return {r["id"]: dict(r, ok=G[r["id"]]["ok"], gerr=G[r["id"]]["err"]) for r in map(json.loads, open(f)) if r["id"] in G}


def visible(r):
    return any(any(st.get("err") or []) or st.get("loop") for t in r["turns"] for st in t)


def util(r):
    return float(r["ok"]) - LAM / 100 * r["tok"] / 1000


def boot_gap(a, b, B=2000):
    """bootstrap over items of mean(a) - mean(b), a / b: {item: [values]} (item-seeds grouped by item)"""
    ids = sorted(set(a) | set(b)); rng = random.Random(0); out = []
    for _ in range(B):
        xs, ys = [], []
        for i in (rng.choice(ids) for _ in ids):
            xs += a.get(i, []); ys += b.get(i, [])
        if xs and ys:
            out.append(sum(xs) / len(xs) - sum(ys) / len(ys))
    out.sort()
    return 100 * out[int(.025 * len(out))], 100 * out[int(.975 * len(out)) - 1]


def main():
    tags = sys.argv[1:] or ["q14a", "q35", "q8b"]
    verdict = {k: [] for k in ("P1", "P2", "P3", "P4", "P5")}
    for tag in tags:
        D = {(a, s): load(tag, a, s) for a in ARMS for s in SEEDS}
        if any(v is None for v in D.values()):
            print(f"=== {tag}: missing rows or grades for {[k for k, v in D.items() if v is None]}")
            continue
        ids = sorted(set.intersection(*(set(v) for v in D.values())))
        cat = {i: D[("N", SEEDS[0])][i]["cat"] for i in ids}
        print(f"=== {tag}: {len(ids)} items x {len(SEEDS)} seeds")
        mean = lambda a, i, f: sum(f(D[(a, s)][i]) for s in SEEDS) / len(SEEDS)
        for c in sorted(set(cat.values())) + ["all"]:
            jj = [i for i in ids if c in ("all", cat[i])]
            print(f"  {c:>22} ({len(jj)}): " + " | ".join(
                f"{a} {100 * sum(mean(a, i, lambda r: r['ok']) for i in jj) / len(jj):.1f}% @ {sum(mean(a, i, lambda r: r['tok']) for i in jj) / len(jj) / 1000:.2f}k"
                f" u {100 * sum(mean(a, i, util) for i in jj) / len(jj):.1f}" for a in ARMS))
        for a in ARMS:
            R = [D[(a, s)][i] for s in SEEDS for i in ids]
            print(f"  {a}: think steps {sum(r['n_think'] for r in R) / len(R):.2f} of {sum(r['n_steps'] for r in R) / len(R):.2f}; "
                  f"with a loop {100 * sum(any(st.get('loop') for t in r['turns'] for st in t) for r in R) / len(R):.1f}%; "
                  f"with an error {100 * sum(any(any(st.get('err') or []) for t in r['turns'] for st in t) for r in R) / len(R):.1f}%; "
                  f"BFCL errors {Counter(r['gerr'] for r in R if not r['ok']).most_common(4)}")
        tests = (("P1", "T - N accuracy", "T", "N", lambda r: float(r["ok"])), ("P2", "E - T utility", "E", "T", util),
                 ("P3", "E - N utility", "E", "N", util), ("P4", "F - E utility", "F", "E", util))
        for k, name, a, b, f in tests:
            g = ci({i: mean(a, i, f) - mean(b, i, f) for i in ids})
            print(f"  MT-{k} {name}: {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
            verdict[k].append((tag, g[1] > 0, g))
        # MT-P5 and N's strata (item-seeds)
        st, gap = {}, {"V": {}, "S": {}}
        for s in SEEDS:
            for i in ids:
                n = D[("N", s)][i]; v = visible(n)
                key = ("R" if n["ok"] else "W") + ("V" if v else "S")
                st.setdefault(key, []).append((D[("E", s)][i]["ok"], D[("T", s)][i]["ok"]))
                gap["V" if v else "S"].setdefault(i, []).append(float(D[("E", s)][i]["ok"]) - float(n["ok"]))
        wrong = len(st.get("WV", [])) + len(st.get("WS", []))
        share = len(st.get("WV", [])) / max(1, wrong)
        ev = sum(sum(x) for x in gap["V"].values()) / max(1, sum(map(len, gap["V"].values())))
        es = sum(sum(x) for x in gap["S"].values()) / max(1, sum(map(len, gap["S"].values())))
        lo, hi = boot_gap(gap["V"], gap["S"])
        print("  N's strata (item-seeds): " + "; ".join(f"{k} {len(v)}: E right {100 * sum(e for e, _ in v) / len(v):.1f}%, T right "
                                                       f"{100 * sum(t for _, t in v) / len(v):.1f}%" for k, v in sorted(st.items())))
        print(f"  MT-P5: visible share of N's wrong item-seeds {100 * share:.1f}% ({len(st.get('WV', []))} / {wrong}); E - N accuracy on N-visible "
              f"{100 * ev:+.2f}, on N-silent {100 * es:+.2f} (gap {100 * (ev - es):+.2f} [{lo:+.2f}, {hi:+.2f}])")
        verdict["P5"].append((tag, share >= 0.5 and ev > es, (100 * share, 100 * ev, 100 * es)))
        sil = [i for i in ids if not any(visible(D[("N", s)][i]) for s in SEEDS)]
        if sil:
            g = ci({i: mean("T", i, lambda r: float(r["ok"])) - mean("E", i, lambda r: float(r["ok"])) for i in sil})
            print(f"  T - E accuracy on items N never shows a failure on ({len(sil)}): {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
    print("*** " + "; ".join(f"MT-{k} {sum(x[1] for x in v)} / {len(v)} ({', '.join(t for t, ok, _ in v if ok) or '-'})"
                             for k, v in verdict.items()))


if __name__ == "__main__":
    main()
