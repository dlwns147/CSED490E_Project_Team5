"""DT (docs/prereg/PREREG_DT.md): the fine-tuned Qwen3-8B (q8bsft, no fact) vs base Qwen3-8B without a fact (free) and with the label-free
library (formx), on the held-out benchmarks (OptiBench: the HO-TF third as pre-registered, and all 605), 3 seeds; paired 95% intervals.
Also the usage-crash census and the leak (share of running, value-printing programs that are wrong).
usage: python analyze_dt.py [tag]   (default q8bsft)"""
import os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, _rows, problems  # noqa: E402

ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")
USAGE = re.compile(r"^(AttributeError|ModuleNotFoundError|ImportError)\b", re.M)


def ci(d, B=2000):
    ids = sorted(d); n = len(ids); rng = random.Random(0)
    bs = sorted(sum(d[rng.choice(ids)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d.values()) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B) - 1]


def main():
    sft = sys.argv[1] if len(sys.argv) > 1 else "q8bsft"
    third = {p["id"] for p in problems("optibench")[0::3]}
    for b, sub in (("optibench", third), ("optibench", None), ("bwor", None), ("logior", None), ("optmath", None)):
        arms = {"base free": f"q8b_{b}_free", "base + library": f"q8b_{b}_formx", "fine-tuned free": f"{sft}_{b}_free"}
        R = {k: {s: {r["id"]: r for r in _rows(f"{RES}/opt_{v}_s{s}.jsonl")} for s in (1, 2, 3)} for k, v in arms.items()}
        ids = [i for i in R["fine-tuned free"][1] if all(i in R[k][s] for k in R for s in (1, 2, 3)) and (sub is None or i in sub)]
        if not ids:
            print(f"=== {b}: no rows"); continue
        acc = {k: 100 * sum(R[k][s][i]["correct"] for s in (1, 2, 3) for i in ids) / (3 * len(ids)) for k in R}
        tok = {k: sum(R[k][s][i].get("out_tokens") or 0 for s in (1, 2, 3) for i in ids) / (3 * len(ids)) / 1000 for k in R}
        stats = {}
        for k in R:
            rows = [R[k][s][i] for s in (1, 2, 3) for i in ids]
            run = [r for r in rows if ok_(r)]
            stats[k] = (100 * sum(r.get("status") == "re" and bool(USAGE.search(r.get("err") or "")) for r in rows) / len(rows),
                        100 * sum(not r["correct"] for r in run) / max(1, len(run)))
        name = b + (" (third)" if sub else "")
        print(f"=== {name} ({len(ids)} problems): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k]:.2f}k (usage crashes {stats[k][0]:.1f}%, leak {stats[k][1]:.0f}%)" for k in R))
        for k in ("base free", "base + library"):
            mu, lo, hi = ci({i: sum(R["fine-tuned free"][s][i]["correct"] - R[k][s][i]["correct"] for s in (1, 2, 3)) / 3 for i in ids})
            print(f"  fine-tuned free - {k} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
