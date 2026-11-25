"""PREREG_DIFF addendum POR (2026-11-25): proven-optimal re-run. A CP-SAT program that sets its own time limit (max_time_in_seconds,
30 or 60 s in gpt-oss-120b's programs) and prints the incumbent on status FEASIBLE reports a value the solver has NOT proven optimal;
in the census these are most of the 'worse than gold' wrong values on optnew / OptMATH. Policy (no model call, zero tokens): re-run every
stored program whose code sets max_time_in_seconds with the limit raised to LIM s (wall LIM + 60 s), the solver status printed after
Solve; the re-run's value replaces the stored one when the re-run prints a value. CPU seconds reported as the cost.
usage: python wp_optcert.py run <set> <tag> <mode> <seed> [LIM 300]   |   python wp_optcert.py score <set> <tag> <mode>"""
import json, os, random, re, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R3 = f"{ROOT}/results/x3"
TL = re.compile(r"(max_time_in_seconds\s*=\s*)([0-9.eE+]+)")
SOLVE = re.compile(r"^(\s*)(\w+)\s*=\s*(\w+)\.Solve\((\w+)[^)]*\)\s*$", re.M)


def patch(code, lim):
    c = TL.sub(lambda m: m.group(1) + str(float(lim)), code)
    m = SOLVE.search(c)
    if m:
        ind, st, sv, md = m.groups()
        c = c[:m.end()] + f"\n{ind}import sys as _s; print('PORSTATUS', {sv}.StatusName({st}), file=_s.stderr, flush=True)" + c[m.end():]
    return c


def run(st, tag, mode, seed, lim):
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    from sandbox import run_python
    src = f"{R3}/opt_{tag}_{st}_{mode}_s{seed}.jsonl"
    out = f"{R3}/por_{tag}_{st}_{mode}_s{seed}.jsonl"
    rows = [json.loads(l) for l in open(src)]
    todo = [r for r in rows if r.get("code") and TL.search(r["code"]) and "cp_model" in r["code"]]

    def one(r):
        t0 = time.time()
        x = run_python(patch(r["code"], lim), "", timeout=lim + 60, mem_bytes=8 << 30, cpu_s=64 * (lim + 60))
        o = (x.stdout if x.status == "ok" else "") or ""
        lines = [l for l in o.strip().splitlines() if l.strip()]
        pred = RN.value_of(lines[-1]) if lines else None
        m = re.search(r"PORSTATUS (\w+)", x.stderr or "")
        return {"id": r["id"], "old_pred": r["pred"], "old_correct": r["correct"], "status": x.status, "solver": m.group(1) if m else None,
                "pred": pred, "correct": RN.correct(pred, r["gold"]) if pred is not None else False, "wall": round(time.time() - t0, 1)}
    with ThreadPoolExecutor(int(os.environ.get("POR_PAR", 4))) as ex, open(out, "w") as f:
        for z in ex.map(one, todo):
            f.write(json.dumps(z) + "\n"); f.flush()


def score(st, tag, mode):
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    for s in (1, 2):
        p, q = f"{R3}/opt_{tag}_{st}_{mode}_s{s}.jsonl", f"{R3}/por_{tag}_{st}_{mode}_s{s}.jsonl"
        if not (os.path.exists(p) and os.path.exists(q)):
            continue
        A = {json.loads(l)["id"]: json.loads(l) for l in open(p)}; Z = {json.loads(l)["id"]: json.loads(l) for l in open(q)}
        new = {i: (bool(Z[i]["correct"]) if i in Z and Z[i]["pred"] is not None else bool(A[i]["correct"])) for i in A}
        old = {i: bool(A[i]["correct"]) for i in A}
        ids = sorted(A); d = [100 * (new[i] - old[i]) for i in ids]; rng = random.Random(1)
        bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
        sol = {}
        for z in Z.values():
            sol[z["solver"]] = sol.get(z["solver"], 0) + 1
        print(f"{st} {tag} {mode} s{s}: re-run {len(Z)} of {len(A)}; solver status {sol}; accuracy {100*sum(old.values())/len(ids):.1f}% -> "
              f"{100*sum(new.values())/len(ids):.1f}%  (gained {sum(new[i] and not old[i] for i in ids)}, lost {sum(old[i] and not new[i] for i in ids)}); "
              f"new - old {sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}] points at 0 tokens; re-run wall {sum(z['wall'] for z in Z.values())/max(1,len(Z)):.0f} s each")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]) if len(sys.argv) > 6 else 300)
    else:
        score(sys.argv[2], sys.argv[3], sys.argv[4])
