"""Final zebra table (144 puzzles): code+snippet+status vs code (no snippet), single samples and verified best-of-k (exact clue check), vs direct+think."""
import json, os
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
L = lambda t: {r["key"]: r for r in map(json.loads, open(f"{RES}/zebra_{t}.jsonl"))} if os.path.exists(f"{RES}/zebra_{t}.jsonl") else None
rng = np.random.default_rng(0)
for m in ["8b", "14b", "32b"]:
    out = []
    for arm in ["docst", "code"]:
        S = [d for d in (L(f"F_z{m}_{arm}_s{s}") for s in (1, 2, 3)) if d]
        if not S: continue
        keys = sorted(S[0]); big = [k for k in keys if k.startswith(("5x5", "6x5"))]
        singles = [np.mean([s[k]["exact"] for k in keys]) for s in S]
        bok = [np.mean([any(s[k]["exact"] for s in S[:kk]) for k in keys]) for kk in range(1, len(S) + 1)]
        out.append(f"{arm}: singles {'/'.join(f'{x:.2f}' for x in singles)} best-of-k {' '.join(f'{x:.2f}' for x in bok)} "
                   f"(5x5+6x5 at k={len(S)}: {sum(any(s[k]['exact'] for s in S) for k in big)}/{len(big)})")
    d = L(f"F_z{m}_thinkdirect_s1")
    if d:
        big = [k for k in d if k.startswith(("5x5", "6x5"))]
        out.append(f"direct+think {np.mean([r['exact'] for r in d.values()]):.2f} (big {sum(d[k]['exact'] for k in big)}/{len(big)}, tok {np.mean([r['tokens'] for r in d.values()])/1000:.1f}k)")
    print(m, " | ".join(out))
