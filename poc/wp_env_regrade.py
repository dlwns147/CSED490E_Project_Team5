"""REGRADE (PREREG_DIFF, 2026-11-25): stored CP-SAT word-problem programs of ours re-run in the corrected environment (INT_MAX / INT_MIN = +-cp_model.INT32_MAX);
rows whose program does not use the constants are copied unchanged. Writes opt_<tag>_<set>_<mode>E_s<seed>.jsonl. usage: python wp_env_regrade.py <glob of opt_*_s*.jsonl>"""
import glob, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python
PRE = "from ortools.sat.python import cp_model as _cm\n_cm.INT_MAX = 2 ** 31 - 1\n_cm.INT_MIN = -(2 ** 31 - 1)\n"
import run_nlopt as RN


def one(r):
    c = r.get("code") or ""
    if "cp_model" not in c or not re.search(r"\bINT_(MAX|MIN)\b", c):
        return r, False
    x = run_python(PRE + c, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600)
    out = (x.stdout if x.status == "ok" else "") or ""
    L = [l for l in out.strip().splitlines() if l.strip()]
    if r.get("mode", "").startswith("freev"):   # its last line is the objective, as at generation time
        pass
    p = RN.value_of(L[-1]) if L else None
    n = dict(r, pred=p, status=x.status, stdout=out[-300:], correct=RN.correct(p, r["gold"]) if p is not None else False)
    return n, True


for f in sorted(x for a in sys.argv[1:] for x in glob.glob(a)):
    b = os.path.basename(f)
    m = re.match(r"(opt_.*)_(thinkfreen|freev)_s(\d+)\.jsonl$", b)
    if not m:
        continue
    R = [json.loads(l) for l in open(f)]
    with ThreadPoolExecutor(8) as ex:
        Z = list(ex.map(one, R))
    new = [z for z, _ in Z]
    with open(os.path.join(os.path.dirname(f), f"{m.group(1)}_{m.group(2)}E_s{m.group(3)}.jsonl"), "w") as o:
        o.write("".join(json.dumps(z) + "\n" for z in new))
    ch = sum(t and bool(a["correct"]) != bool(b2["correct"]) for a, (b2, t) in zip(R, Z))
    print(f"{b}: {len(R)} rows, re-run {sum(t for _, t in Z)}, grade changed {ch} (gained {sum(bool(n2['correct']) and not bool(o2['correct']) for o2, n2 in zip(R, new))}, "
          f"lost {sum(bool(o2['correct']) and not bool(n2['correct']) for o2, n2 in zip(R, new))}); accuracy {100*sum(bool(r['correct']) for r in R)/len(R):.1f} -> {100*sum(bool(r['correct']) for r in new)/len(R):.1f}; "
          f"both numeric and different {sum(isinstance(o2['pred'], float) and isinstance(n2['pred'], float) and not RN.correct(o2['pred'], str(n2['pred'])) for o2, n2 in zip(R, new))}", flush=True)
