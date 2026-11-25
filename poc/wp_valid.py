"""VALID (PREREG_DIFF, 2026-11-25): what the solver itself says about a rejected model, given back for one repair. A CP-SAT program whose solver
status is MODEL_INVALID (or UNKNOWN) prints 'No Best Solution' like an infeasible one, though nothing was solved. Trigger = the status of a
re-run of the STORED program with one line inserted after `<status> = <solver>.Solve(<model>)` (poc/wp_nbs_diag.py); no text rule.
Arms on the triggered rows (others keep the stored answer): V = one repair turn with the problem, the program, the status and
model.Validate()'s message; R = a fresh thinking program for the problem (the resample baseline, MC-RS). INFEASIBLE is never repaired
(NL4OPT has 17 true 'No Best Solution' answers). usage: python wp_valid.py run <set> <tag> <mode> <seed> | score <set> [<set> ...] <tag> <mode> <seed>"""
import json, os, random, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R3 = f"{ROOT}/results/x3"
PAT = re.compile(r"^(\s*)(\w+)\s*=\s*(\w+)\.Solve\((\w+)[^)]*\)\s*$", re.M)
FIX = ("{q}\n\nYour earlier program for this problem:\n```python\n{code}\n```\nThe solver did not solve this model: it returned the status {status}. "
       "Its validation message: {msg}\nThis status means that the model was rejected before any search, so it says nothing about whether the "
       "problem has a solution. Find the cause in the program and write the corrected program. The program receives no input (stdin is empty). "
       "Print ONLY the optimal objective value. If the problem has no optimal solution (infeasible or unbounded), print exactly `No Best "
       "Solution`. Give the program in a single ```python code block.")


def patch(code):
    m = PAT.search(code or "")
    if not m or "cp_model" not in code:
        return None
    ind, st, sv, md = m.groups()
    return code[:m.end()] + (f"\n{ind}import sys as _s; print('VALSTATUS', {sv}.StatusName({st}), repr({md}.Validate())[:400], file=_s.stderr, flush=True)") + code[m.end():]


def trigger(r, run_python):
    c = patch(r.get("code"))
    if c is None:
        return None
    x = run_python(c, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600)
    m = re.search(r"VALSTATUS (\w+) (.*)", x.stderr or "")
    return (m.group(1), m.group(2).strip()) if m else None


def run(st, tag, mode, seed):
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    from llm import chat, last_block
    from sandbox import run_python
    P = {p["id"]: p for p in RN.problems()}
    rows = [json.loads(l) for l in open(f"{R3}/opt_{tag}_{st}_{mode}_s{seed}.jsonl")]
    out = f"{R3}/valid_{tag}_{st}_{mode}_s{seed}.jsonl"
    with ThreadPoolExecutor(12) as ex:
        T = {r["id"]: t for r, t in zip(rows, ex.map(lambda r: trigger(r, run_python), rows))}
    trig = [r for r in rows if T[r["id"]] and T[r["id"]][0] in ("MODEL_INVALID", "UNKNOWN")]
    print(st, "statuses", {k: sum(1 for t in T.values() if t and t[0] == k) for k in {t[0] for t in T.values() if t}}, "triggered", len(trig), "of", len(rows), flush=True)

    def solve(text):
        code = last_block(text or "", ("python", "py", "python3"))
        x = run_python(code, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600) if code else None
        o = (x.stdout if x and x.status == "ok" else "") or ""
        L = [l for l in o.strip().splitlines() if l.strip()]
        return RN.value_of(L[-1]) if L else None

    def one(r):
        p = P[r["id"]]; stt, msg = T[r["id"]]; sd = 9000 + zlib.crc32(r["id"].encode()) % 997
        v = chat(FIX.format(q=p["q"], code=r["code"], status=stt, msg=msg), think=True, max_tokens=16000, temperature=0.7, seed=sd)
        f = chat(RN.P_FREEN.format(q=p["q"]), think=True, max_tokens=16000, temperature=0.7, seed=sd + 5000)
        pv, pf = solve(v["text"]), solve(f["text"])
        return {"id": r["id"], "status": stt, "msg": msg, "old_pred": r["pred"], "old_correct": r["correct"], "old_tok": r["out_tokens"], "gold": p["gold"],
                "v_pred": pv, "v_correct": RN.correct(pv, p["gold"]) if pv is not None else False, "v_tok": v.get("out_tokens"),
                "r_pred": pf, "r_correct": RN.correct(pf, p["gold"]) if pf is not None else False, "r_tok": f.get("out_tokens")}
    with ThreadPoolExecutor(32) as ex, open(out, "w") as fo:
        for z in ex.map(one, trig):
            fo.write(json.dumps(z) + "\n"); fo.flush()


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d)/len(d):+.2f} [{b[100]:+.2f}, {b[3899]:+.2f}]"


def score(sets, tag, mode, seed):
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    N, V, R, tn, tr = [], [], [], 0, 0
    for st in sets:
        rows = [json.loads(l) for l in open(f"{R3}/opt_{tag}_{st}_{mode}_s{seed}.jsonl")]
        Z = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R3}/valid_{tag}_{st}_{mode}_s{seed}.jsonl")}
        tr += len(Z); tn += len(rows)
        for r in rows:
            t0 = int(r["out_tokens"] or 0); z = Z.get(r["id"]); N.append((bool(r["correct"]), t0))
            V.append((bool(z["v_correct"]), t0 + int(z["v_tok"] or 0)) if z else N[-1]); R.append((bool(z["r_correct"]), t0 + int(z["r_tok"] or 0)) if z else N[-1])
        print(f"{st}: {len(rows)} rows, triggered {len(Z)}; of the triggered, old right {sum(z['old_correct'] for z in Z.values())}, repaired right "
              f"{sum(z['v_correct'] for z in Z.values())}, resampled right {sum(z['r_correct'] for z in Z.values())}; tokens per triggered: V "
              f"{sum(int(z['v_tok'] or 0) for z in Z.values())/max(1,len(Z)):.0f}, R {sum(int(z['r_tok'] or 0) for z in Z.values())/max(1,len(Z)):.0f}")
    f = lambda X: f"accuracy {100*sum(a for a, _ in X)/len(X):.1f}%  tokens {sum(t for _, t in X)/len(X)/1000:.2f}k  utility {sum(U(a, t) for a, t in X)/len(X):.2f}"
    print(f"pooled n={tn}, triggered {tr}\n  N (stored)  {f(N)}\n  V (repair)  {f(V)}\n  R (resample){f(R)}")
    u = lambda X: [U(a, t) for a, t in X]; acc = lambda X: [100 * a for a, _ in X]
    for lab, X, Y in (("V − N", V, N), ("V − R", V, R), ("R − N", R, N)):
        print(f"  {lab}: accuracy {ci([a - b for a, b in zip(acc(X), acc(Y))])}  utility {ci([a - b for a, b in zip(u(X), u(Y))])}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
    else:
        score(sys.argv[2:-3], sys.argv[-3], sys.argv[-2], int(sys.argv[-1]))
