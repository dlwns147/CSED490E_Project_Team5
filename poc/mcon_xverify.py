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




def build2():
    """addendum MC2: the think-then-program samples' boxed answers parsed into objects by the problem's own parser (no model code run)"""
    import types
    if "llm" not in sys.modules:
        m = types.ModuleType("llm"); m.chat = m.last_block = m.think_cuts = None; sys.modules["llm"] = m
    import run_compute as RC
    RC.problems("mcon")
    out = open(f"{R}/mcon_xv_objs2.jsonl", "w")
    for m in ("q8b", "oss20", "oss120"):
        for s in (1, 2, 3):
            p = f"{R}/mcon_{m}_thinkp_s{s}.jsonl"
            if not os.path.exists(p):
                continue
            for l in open(p):
                r = json.loads(l); obj = None
                try:
                    res = RC._MC[r["id"]].parse_and_check([{"role": "assistant", "content": r.get("stdout") or ""}])
                    obj = repr(res[0]) if res and res[0] is not None else None
                except Exception:
                    obj = None
                out.write(json.dumps({"id": r["id"], "src": f"{m}T_s{s}", "obj": obj, "correct": str(r.get("correct")) == "True",
                                      "tok": int(r.get("out_tokens") or 0)}) + "\n")
    out.close()


def check2():
    from sandbox import run_python
    Rw = rows()
    objs = [json.loads(l) for l in open(f"{R}/mcon_xv_objs2.jsonl")]
    jobs = [(o, v) for o in objs if o["obj"] for (pid, v) in Rw if pid == o["id"]]
    def one(t):
        o, v = t
        code = "__name__ = '__xv__'\n" + Rw[(o["id"], v)]["code"] + f"\n\nobj = {o['obj']}\nprint('__V__', bool(verify(obj)))\n"
        r = run_python(code, "", timeout=60, mem_bytes=4 << 30)
        m = [l for l in (r.stdout or "").splitlines() if l.startswith("__V__")]
        return {"id": o["id"], "cand": o["src"], "ver": v, "pass": (m[-1].split()[-1] == "True") if (r.status == "ok" and m) else None}
    with ThreadPoolExecutor(int(os.environ.get("XV_PAR", 16))) as ex, open(f"{R}/mcon_xv_checks2.jsonl", "w") as f:
        for o in ex.map(one, jobs):
            f.write(json.dumps(o) + "\n"); f.flush()


def score():
    import random
    from collections import defaultdict
    Rw = rows()
    C = defaultdict(dict)
    for l in open(f"{R}/mcon_xv_checks.jsonl"):
        x = json.loads(l)
        if x["pass"] is not None:
            C[(x["id"], x["cand"])][x["ver"]] = x["pass"]
    fam = lambda v: v.split("_s")[0]
    probs = defaultdict(list)
    for (pid, src), r in Rw.items():
        probs[pid].append(src)
    right = {k: str(r["correct"]) == "True" for k, r in Rw.items()}
    a = {f: 0.8 for f in ("q8b", "oss20", "oss120")}; b = {f: 0.3 for f in a}; pi = 0.3
    def post(pid, src):
        lr, lw = math.log(pi), math.log(1 - pi)
        for v, p in C.get((pid, src), {}).items():
            f = fam(v); lr += math.log(a[f] if p else 1 - a[f]); lw += math.log(b[f] if p else 1 - b[f])
        m = max(lr, lw); return math.exp(lr - m) / (math.exp(lr - m) + math.exp(lw - m))
    for _ in range(50):   # Dawid-Skene EM over verifier families (label-free)
        na = defaultdict(lambda: [1.0, 2.0]); nb = defaultdict(lambda: [1.0, 2.0]); sp = 0; n = 0
        for (pid, src), vs in C.items():
            q = post(pid, src); sp += q; n += 1
            for v, p in vs.items():
                f = fam(v); na[f][0] += q * p; na[f][1] += q; nb[f][0] += (1 - q) * p; nb[f][1] += (1 - q)
        a = {f: na[f][0] / na[f][1] for f in a}; b = {f: nb[f][0] / nb[f][1] for f in b}; pi = sp / max(n, 1)
    print("fitted P(pass|right)", {f: round(x, 2) for f, x in a.items()}, "P(pass|wrong)", {f: round(x, 2) for f, x in b.items()}, "prior", round(pi, 2))
    res = defaultdict(dict)
    for pid, srcs in probs.items():
        cands = [s for s in srcs if (pid, s) in C]
        ds = max(cands, key=lambda s: post(pid, s)) if cands else None
        mv = max(cands, key=lambda s: sum(C[(pid, s)].values())) if cands else None
        res["DS cross-verify"][pid] = right.get((pid, ds), False) if ds else False
        res["most passing verifiers"][pid] = right.get((pid, mv), False) if mv else False
        res["any progc right (oracle)"][pid] = any(right[(pid, s)] for s in srcs)
        for f in ("q8b", "oss20", "oss120"):
            res[f"single {f} progc (mean of seeds)"][pid] = sum(right.get((pid, f"{f}_s{s}"), False) for s in (1, 2, 3)) / 3
    ids = sorted(probs)
    for k, d in res.items():
        print(f"  {k:36s} {100 * sum(d[i] for i in ids) / len(ids):5.1f}%")
    for base in ("single oss120 progc (mean of seeds)", "most passing verifiers"):
        dd = {i: 100 * (res["DS cross-verify"][i] - res[base][i]) for i in ids}
        rng = random.Random(1); B = 4000
        bs = sorted(sum(dd[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B))
        print(f"  DS - {base}: {sum(dd.values()) / len(ids):+.2f} [{bs[int(.025 * B)]:+.2f}, {bs[int(.975 * B) - 1]:+.2f}] p={(sum(x <= 0 for x in bs) + 1) / (B + 1):.4f}")


import math  # noqa: E402
if __name__ == "__main__":
    {"build": build, "check": check, "build2": build2, "check2": check2, "score": score}[sys.argv[1]]()
