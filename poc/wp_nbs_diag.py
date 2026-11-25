"""Diagnostic (descriptive, 2026-11-25): what is behind a word-problem program's 'No Best Solution'? optnew has no infeasible gold, yet
32 of 93 gpt-oss-120b thinking programs (seed 1) print it. 48 of the 59 (seeds 1-2) use OR-Tools CP-SAT, whose non-OPTIMAL/FEASIBLE
status covers INFEASIBLE, MODEL_INVALID (e.g. a non-integer coefficient) and UNKNOWN (no answer in time). Re-run each such program with
one line inserted after `<status> = <solver>.Solve(<model>)` that prints the status name and model.Validate(); other libraries' runs
are re-run unchanged and reported as 'other'. usage: python wp_nbs_diag.py <glob of result files>"""
import collections, glob, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python

PAT = re.compile(r"^(\s*)(\w+)\s*=\s*(\w+)\.Solve\((\w+)[^)]*\)\s*$", re.M)


def patch(code):
    m = PAT.search(code)
    if not m or "cp_model" not in code:
        return None
    ind, st, sv, md = m.groups()
    ins = (f"\n{ind}print('NBSDIAG', {sv}.StatusName({st}), repr({md}.Validate())[:300], "
           f"{sv}.WallTime() if hasattr({sv}, 'WallTime') else -1, flush=True)")
    return code[:m.end()] + ins + code[m.end():]


def one(r):
    c = patch(r["code"] or "")
    if c is None:
        return {"id": r["id"], "kind": "other"}
    z = run_python(c, "", timeout=600, mem_bytes=8 << 30, cpu_s=4800)
    m = re.search(r"NBSDIAG (\w+) (.*?) ([\d.]+|-1)\n", z.stdout or "")
    return {"id": r["id"], "kind": m.group(1) if m else f"nodiag:{z.status}", "validate": m.group(2) if m else "", "wall": m.group(3) if m else ""}


rows = [dict(json.loads(l), f=os.path.basename(f)) for f in sorted(glob.glob(sys.argv[1])) for l in open(f)]
rows = [r for r in rows if r.get("pred") == "NBS"]
with ThreadPoolExecutor(int(os.environ.get("DIAG_PAR", 8))) as ex:
    res = list(ex.map(one, rows))
print(len(res), collections.Counter(z["kind"] for z in res))
for z in res:
    if z["kind"] == "MODEL_INVALID":
        print(z["id"], z["validate"][:200])
json.dump(res, open(os.environ.get("DIAG_OUT", "/dev/null"), "w"))
