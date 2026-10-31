"""LCM (docs/prereg/PREREG_LCM.md): the summary over the cells of poc/lcm.py (results/lcm/*.json): per cell the planner (k = 30, k = 0,
independent errors) against the default cascade, the 30-label pilot's policy and the oracle fixed policy (utility, accuracy, tokens;
paired 95% intervals over questions), the chosen K and concentrations; then LCM-P1..P4.
usage: python3.11 poc/analyze_lcm.py"""
import glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
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
