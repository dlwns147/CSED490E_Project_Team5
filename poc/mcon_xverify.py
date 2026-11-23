"""PREREG_DIFF addendum MC (2026-11-23): cross-verification on MathConstruct. Step `build`: run each stored progc program's construct()
and keep repr(obj); step `check`: run every OTHER progc sample's verify() on each candidate object. Both in the sandbox.
usage: python3 mcon_xverify.py build | check | score   -> results/x44/mcon_xv_objs.jsonl, mcon_xv_checks.jsonl"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
SAMPLES = [(m, s) for m in ("q8b", "oss20", "oss120") for s in (1, 2, 3)]


def rows():
    out = {}
    for m, s in SAMPLES:
        p = f"{R}/mcon_{m}_progc_s{s}.jsonl"
        if os.path.exists(p):
            for l in open(p):
                r = json.loads(l)
                if r.get("code"):
                    out[(r["id"], f"{m}_s{s}")] = r
    return out


def build():
    from sandbox import run_python
    Rw = rows()
    def one(k):
        code = "__name__ = '__xv__'\n" + Rw[k]["code"] + "\n\nimport sys\nsys.setrecursionlimit(100000)\nprint('__OBJ__' + repr(construct()))\n"
        r = run_python(code, "", timeout=60, mem_bytes=4 << 30)
        m = [l for l in (r.stdout or "").splitlines() if l.startswith("__OBJ__")]
        return {"id": k[0], "src": k[1], "obj": m[-1][7:][:200000] if (r.status == "ok" and m) else None, "status": r.status}
    with ThreadPoolExecutor(int(os.environ.get("XV_PAR", 16))) as ex, open(f"{R}/mcon_xv_objs.jsonl", "w") as f:
        for o in ex.map(one, list(Rw)):
            f.write(json.dumps(o) + "\n"); f.flush()


def check():
    from sandbox import run_python
    Rw = rows()
    objs = [json.loads(l) for l in open(f"{R}/mcon_xv_objs.jsonl")]
    jobs = [(o, v) for o in objs if o["obj"] for (pid, v) in Rw if pid == o["id"] and v != o["src"]]
    def one(t):
        o, v = t
        code = "__name__ = '__xv__'\n" + Rw[(o["id"], v)]["code"] + f"\n\nobj = {o['obj']}\nprint('__V__', bool(verify(obj)))\n"
        r = run_python(code, "", timeout=60, mem_bytes=4 << 30)
        m = [l for l in (r.stdout or "").splitlines() if l.startswith("__V__")]
        return {"id": o["id"], "cand": o["src"], "ver": v, "pass": (m[-1].split()[-1] == "True") if (r.status == "ok" and m) else None}
    with ThreadPoolExecutor(int(os.environ.get("XV_PAR", 16))) as ex, open(f"{R}/mcon_xv_checks.jsonl", "w") as f:
        for o in ex.map(one, jobs):
            f.write(json.dumps(o) + "\n"); f.flush()


if __name__ == "__main__":
    {"build": build, "check": check}[sys.argv[1]]()
