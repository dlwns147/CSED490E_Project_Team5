"""X4-P1, log-prob half (PREREG_X3.md): in Qwen proofs with raw log-probs, are names that do not exist in Mathlib written with lower
token confidence than names that exist? Names = dotted / underscored identifiers in the proof body; "invented" = reported by Lean as
unknown identifier / constant; "existing" = in the dumped Mathlib name list (392,933). Score = min log-prob over the name's tokens at
its first occurrence in the proof. usage: python analyze_x4_lp.py <tag>"""
import bisect, itertools, json, os, re, sys, statistics as st
_DATA = os.environ.get("POC_DATA", "/NAS/SJ/POSTECH/nlp_data")   # Slurm server (2026-10-22): external data; old server: /SSD/lean_postech

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x4")
NAMES = set(open(_DATA + "/mathlib_names.txt").read().split("\n"))


def auroc(neg, pos):
    p = sorted(pos); n = 0.0
    for x in neg:
        lo, hi = bisect.bisect_left(p, x), bisect.bisect_right(p, x); n += (len(p) - hi) + 0.5 * (hi - lo)
    return n / (len(neg) * len(p)) if neg and pos else float("nan")


tag = sys.argv[1]
inv, real = [], []
for r in map(json.loads, open(f"{RES}/lean_{tag}_test.jsonl")):
    toks, lps, body = r.get("lp_tok") or [], r.get("lp") or [], r.get("body")
    if not toks or not body:
        continue
    joined = "".join(toks); base = joined.rfind(body[:80])
    if base < 0:
        continue
    starts = list(itertools.accumulate([0] + [len(t) for t in toks]))
    seen = set()
    for m in re.finditer(r"(?<![\w.'])([A-Za-z][\w']*(?:\.[A-Za-z_][\w']*)+|[a-z][a-z0-9]*_[\w']+)", body):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        a, b = base + m.start(1), base + m.end(1)
        idx = [i for i in range(len(toks)) if starts[i] < b and starts[i + 1] > a]
        if not idx:
            continue
        s = min(lps[i] for i in idx)
        if name in (r.get("unknown") or []):
            inv.append(s)
        elif name in NAMES:
            real.append(s)
print(f"{tag}: names in proofs: existing {len(real)}, non-existent (Lean: unknown) {len(inv)}; median min log-prob existing "
      f"{st.median(real) if real else float('nan'):.3f}, non-existent {st.median(inv) if inv else float('nan'):.3f}; AUROC (non-existent lower) {auroc(inv, real):.3f}")
