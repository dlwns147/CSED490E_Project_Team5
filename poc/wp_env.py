"""ENV (PREREG_DIFF, 2026-11-25): the zero-token competitor of VALID. The stored programs that VALID triggered on, re-run with cp_model.INT_MAX / INT_MIN
set to the largest accepted domain, +-(2**62 - 1). usage: python wp_env.py <set> [<set> ...]   (reads results/x3/valid_oss120_<set>_thinkfreen_s1.jsonl)"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python
R3 = f"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/results/x3"
PRE = "from ortools.sat.python import cp_model as _cm\n_cm.INT_MAX = 2 ** 62 - 1\n_cm.INT_MIN = -(2 ** 62 - 1)\n"
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d)/len(d):+.2f} [{b[100]:+.2f}, {b[3899]:+.2f}]"


N, V, E = [], [], []
for st in sys.argv[1:]:
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    rows = [json.loads(l) for l in open(f"{R3}/opt_oss120_{st}_thinkfreen_s1.jsonl")]
    Z = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R3}/valid_oss120_{st}_thinkfreen_s1.jsonl")}

    def one(r):
        x = run_python(PRE + r["code"], "", timeout=60, mem_bytes=4 << 30, cpu_s=3600)
        o = (x.stdout if x.status == "ok" else "") or ""; L = [l for l in o.strip().splitlines() if l.strip()]
        p = RN.value_of(L[-1]) if L else None
        return r["id"], p
    with ThreadPoolExecutor(8) as ex:
        got = dict(ex.map(one, [r for r in rows if r["id"] in Z]))
    ok = {i: (RN.correct(p, Z[i]["gold"]) if p is not None else False) for i, p in got.items()}
    print(f"{st}: triggered {len(Z)}: ENV prints a number {sum(isinstance(p, float) for p in got.values())}, NBS {sum(p == 'NBS' for p in got.values())}, nothing {sum(p is None for p in got.values())}; "
          f"ENV right {sum(ok.values())}, V right {sum(z['v_correct'] for z in Z.values())}, both {sum(ok[i] and Z[i]['v_correct'] for i in Z)}")
    for r in rows:
        t0 = int(r["out_tokens"] or 0); z = Z.get(r["id"]); N.append((bool(r["correct"]), t0))
        V.append((bool(z["v_correct"]), t0 + int(z["v_tok"] or 0)) if z else N[-1]); E.append((bool(ok[r["id"]]), t0) if z else N[-1])
f = lambda X: f"accuracy {100*sum(a for a, _ in X)/len(X):.1f}%  tokens {sum(t for _, t in X)/len(X)/1000:.2f}k  utility {sum(U(a, t) for a, t in X)/len(X):.2f}"
print(f"pooled n={len(N)}\n  N    {f(N)}\n  V    {f(V)}\n  ENV  {f(E)}")
for lab, X, Y in (("ENV − N", E, N), ("V − ENV", V, E)):
    print(f"  {lab}: accuracy {ci([100*(a[0]-b[0]) for a, b in zip(X, Y)])}  utility {ci([U(*a)-U(*b) for a, b in zip(X, Y)])}")
