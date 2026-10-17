"""N16b (results/PREREG_N16.md): token log-probs at helper names in geometry programs (stored C1 runs, K8 toolbox).
usage: python analyze_n16b.py"""
import itertools, json, os, re, statistics as st, bisect, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import NEED, with_deps  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def auroc(neg, pos):   # P(score(neg) < score(pos)), ties half
    if not neg or not pos:
        return float("nan")
    p = sorted(pos); n = 0.0
    for x in neg:
        lo, hi = bisect.bisect_left(p, x), bisect.bisect_right(p, x); n += (len(p) - hi) + 0.5 * (hi - lo)
    return n / (len(neg) * len(p))


for m in ("8b", "32b"):
    need, dis, dis_ok, dis_bad = [], [], [], []
    nprog = 0
    for sd in (1, 2, 3):
        for r in map(json.loads, open(f"{RES}/geocross_S2_C1_geox{m}_dis8_t07s{sd}.jsonl")):
            toks, lps, code = r.get("lp_tok") or [], r.get("lp") or [], r.get("code") or ""
            if not toks or not code:
                continue
            nprog += 1
            joined = "".join(toks); starts = list(itertools.accumulate([0] + [len(t) for t in toks]))
            helpers = set(re.findall(r"^def (\w+)\(", code, re.M))
            # the toolbox is copied into the program; the model's own code follows the last helper definition it copied
            offered = set(r.get("distractors") or [])
            body_at = max((joined.find(f"def {h}(") for h in helpers), default=0)
            for h in helpers:
                mm = re.search(rf"(?<![\w.]){h}\(", joined[body_at:])
                # first CALL of h after the definitions block (skip its own `def h(`)
                calls = [x for x in re.finditer(rf"(?<!def )(?<![\w.]){h}\(", joined) if x.start() > body_at]
                if not calls:
                    continue
                a, b = calls[0].start(), calls[0].start() + len(h)
                idx = [i for i in range(len(toks)) if starts[i] < b and starts[i + 1] > a]
                if not idx:
                    continue
                s = min(lps[i] for i in idx)
                if h in offered:
                    dis.append(s); (dis_ok if r["class"] == "correct_all" else dis_bad).append(s)
                elif h in set(with_deps(NEED[r["task"]])):   # only the toolbox's needed helpers (not the model's own functions)
                    need.append(s)
    print(f"Qwen3-{m.upper()}: {nprog} programs; first calls of needed helpers {len(need)}, of distractors {len(dis)}")
    print(f"  min log-prob at the helper name: needed median {st.median(need):.3f}, distractor median {st.median(dis):.3f}; "
          f"AUROC (distractor lower) {auroc(dis, need):.3f}")
    print(f"  distractor calls in wrong vs correct programs: medians {st.median(dis_bad) if dis_bad else float('nan'):.3f} vs "
          f"{st.median(dis_ok) if dis_ok else float('nan'):.3f} (n = {len(dis_bad)} / {len(dis_ok)}); AUROC (wrong lower) {auroc(dis_bad, dis_ok):.3f}")
