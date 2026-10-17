"""PoC G2 summaries.  usage: analyze_geo.py <tag> [<tag> ...]
accuracy per task x variant; consistency = an instance's answers over the 6 non-degenerate transforms agree with
each other (after undoing the x9 scale for area2/close), reported both as 'consistent' and 'consistent & correct'."""
import json
import sys
from collections import defaultdict

import numpy as np

RES = "/NAS/SJ/POSTECH/nlp/results"
VARS = ["identity", "translate", "rot90", "mirror", "permute", "scale", "big", "degen"]
INV = ["identity", "translate", "rot90", "mirror", "permute", "scale", "big"]


def norm(task, variant, pred):
    if pred is None:
        return None
    if variant == "scale" and task in ("area2", "close"):
        try:
            v = int(pred)
            return str(v // 9) if v % 9 == 0 else f"{pred}/9"
        except ValueError:
            return pred
    return pred


for tag in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f"{RES}/geo_{tag}.jsonl")]
    print(f"== {tag}  ({len(rows)} answers; no-answer rate {np.mean([r['pred'] is None for r in rows]):.2f}, "
          f"truncated {np.mean([r['finish'] == 'length' for r in rows]):.2f})")
    acc = defaultdict(lambda: defaultdict(list))
    inst = defaultdict(dict)
    for r in rows:
        acc[r["task"]][r["variant"]].append(r["correct"])
        inst[(r["task"], r["n"], r["inst"])][r["variant"]] = r
    print(f"  {'task':6s} " + " ".join(f"{v[:6]:>6s}" for v in VARS) + "   consist  cons&corr")
    for task in ("hull", "area2", "pip", "segs", "close"):
        cs, cc = [], []
        for (t, n, i), d in inst.items():
            if t != task or not all(v in d for v in INV):
                continue
            vals = {norm(task, v, d[v]["pred"]) for v in INV}
            cs.append(len(vals) == 1 and None not in vals)
            cc.append(all(d[v]["correct"] for v in INV))
        print(f"  {task:6s} " + " ".join(f"{np.mean(acc[task][v]):6.2f}" for v in VARS) +
              f"   {np.mean(cs):6.2f}   {np.mean(cc):6.2f}")
    allv = [r["correct"] for r in rows if r["variant"] in INV]
    print(f"  overall acc (non-degen) {np.mean(allv):.3f}   identity {np.mean([r['correct'] for r in rows if r['variant'] == 'identity']):.3f}"
          f"   degen {np.mean([r['correct'] for r in rows if r['variant'] == 'degen']):.3f}")
