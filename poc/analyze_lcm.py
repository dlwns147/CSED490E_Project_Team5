"""LCM (docs/prereg/PREREG_LCM.md): the summary over the cells of poc/lcm.py (results/lcm/*.json): per cell the planner (k = 30, k = 0,
independent errors) against the default cascade, the 30-label pilot's policy and the oracle fixed policy (utility, accuracy, tokens;
paired 95% intervals over questions), the chosen K and concentrations; then LCM-P1..P4.
usage: python3.11 poc/analyze_lcm.py [--lcm2]   (--lcm2: the addendum, results/lcm2)"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lcm2():
    """LCM-2 (addendum): results/lcm2/*.json; L2-P1..P3 on the development cells, L2-P4 on Spider (set 'spider')"""
    R = [json.load(open(p)) for p in sorted(glob.glob(f"{ROOT}/results/lcm2/*.json"))]
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    for r in R:
        v = r["variants"]
        print(f"{r['task']:<34} n {r['n']:>5}: default {r['fixed']['cascade']:+.2f}; lcm2(30) {v['lcm230']['u']:+.2f} ({v['lcm230']['acc']:.1f}% @ "
              f"{v['lcm230']['ktok']:.2f}k) vs default {f(v['lcm230']['vs_default'])}, vs pilot {f(v['lcm230']['vs_pilot'])}, vs oracle "
              f"{f(v['lcm230']['vs_oracle'])}; lcm2 - lcm {f(r['lcm2_vs_lcm'])}; lcm2(100) {v['lcm2100']['u']:+.2f} vs default "
              f"{f(v['lcm2100']['vs_default'])}")
    dev = [r for r in R if " spider " not in r["task"]]
    sp = [r for r in R if " spider " in r["task"]]
    c = lambda X, g, side: sum((g(r)[1] > 0) if side > 0 else (g(r)[2] < 0) for r in X)
    vd, vp, vl = (lambda r: r["variants"]["lcm230"]["vs_default"]), (lambda r: r["variants"]["lcm230"]["vs_pilot"]), (lambda r: r["lcm2_vs_lcm"])
    print(f"\n*** development cells: {len(dev)}; Spider cells: {len(sp)}")
    print(f"L2-P1 vs default: better {c(dev, vd, 1)}, worse {c(dev, vd, -1)} (needs >= 10, <= 5) -> "
          f"{'holds' if c(dev, vd, 1) >= 10 and c(dev, vd, -1) <= 5 else 'refuted'}")
    print(f"L2-P2 vs LCM: better {c(dev, vl, 1)}, worse {c(dev, vl, -1)} (needs >= 10, <= 3) -> "
          f"{'holds' if c(dev, vl, 1) >= 10 and c(dev, vl, -1) <= 3 else 'refuted'}")
    print(f"L2-P3 vs 30-label pilot: better {c(dev, vp, 1)} (needs >= 12) -> {'holds' if c(dev, vp, 1) >= 12 else 'refuted'}")
    if sp:
        print(f"L2-P4 Spider vs default: better {c(sp, vd, 1)}, worse {c(sp, vd, -1)} of {len(sp)} (needs >= 3 of 4, none worse) -> "
              f"{'holds' if c(sp, vd, 1) >= 3 and c(sp, vd, -1) == 0 else 'refuted'}")


def main():
    if "--lcm2" in sys.argv:
        return lcm2()
    R = [json.load(open(p)) for p in sorted(glob.glob(f"{ROOT}/results/lcm/*.json"))]
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    for r in R:
        ob = max(r["fixed"], key=r["fixed"].get)
        Ks = sorted({m["K"] for m in r["models"] if m["variant"] == "lcm" and m["k"] == 30})
        print(f"{r['task']:<34} n {r['n']:>5}: planner {r['planner']['lcm30']:+6.2f} ({r['planner_acc']['lcm30']:.1f}% @ "
              f"{r['planner_ktok']['lcm30']:.2f}k), best fixed (full set) {ob} {r['fixed'][ob]:+.2f} ({r['fixed_acc'][ob]:.1f}% @ "
              f"{r['fixed_ktok'][ob]:.2f}k); K {Ks}")
        print(f"    vs default {f(r['vs_default'])}; vs 30-label pilot {f(r['vs_pilot'])}; vs oracle {f(r['vs_oracle'])}; "
              f"vs indep {f(r['vs_indep'])}; k=0 vs default {f(r['k0_vs_default'])}; k=0 vs k=30 {f(r['k0_vs_k30'])}")
    n = len(R)
    cnt = lambda key, side: sum((r[key][1] > 0) if side > 0 else (r[key][2] < 0) for r in R)
    print(f"\n*** {n} cells")
    for name, key, need_lo, max_hi in (("LCM-P1 vs default", "vs_default", 16, 3), ("LCM-P2 vs 30-label pilot", "vs_pilot", 16, 3),
                                       ("LCM-P3 vs oracle fixed", "vs_oracle", 8, None), ("LCM-P4 vs independent errors", "vs_indep", 10, 3)):
        lo, hi = cnt(key, 1), cnt(key, -1)
        ok = lo >= need_lo and (max_hi is None or hi <= max_hi)
        print(f"{name}: better {lo}, worse {hi} (needs >= {need_lo} better" + (f", <= {max_hi} worse" if max_hi is not None else "")
              + f") -> {'holds' if ok else 'refuted'}")
    print(f"reported: k=0 vs default better {cnt('k0_vs_default', 1)}, worse {cnt('k0_vs_default', -1)}; k=0 vs k=30 better "
          f"{cnt('k0_vs_k30', 1)}, worse {cnt('k0_vs_k30', -1)}")
    dom = sum(r["planner_acc"]["lcm30"] >= r["fixed_acc"][max(r["fixed"], key=r["fixed"].get)] and
              r["planner_ktok"]["lcm30"] <= r["fixed_ktok"][max(r["fixed"], key=r["fixed"].get)] for r in R)
    print(f"reported: planner at least as accurate and no more tokens than the best fixed policy (any lambda) in {dom} / {n}")


if __name__ == "__main__":
    main()
