"""VRPTW input-format analysis (HANDOFF step 2, server 2): per run, opt / feasible rate, mean output tokens, and the input-format
counterfactual. Each stored final program is re-run (CPU) on its instance twice: with the real 5-field header `n capacity K service horizon`
and with the `service` field removed. Labels: reads_service = feasible on the real input; skips_service = infeasible/failing on the real input
but feasible on the 4-field one (the program reads `n capacity K horizon`); other_fail = fails on both; no_code.
best-of-3 = label-free: among the seeds' feasible solutions per instance, keep the lowest objective (no reference used for the choice).
usage: python analyze_vrptw_stdin.py <tag-prefix> [<tag-prefix> ...]   (a prefix P reads results/co_P_s{1,2,3}.jsonl, or co_P.jsonl if no seeds)"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_co import describe, gen, objective, parse_solution  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"


def feasible_on(code, inst, stdin):
    r = run_python(code, stdin, timeout=40, mem_bytes=4 << 30)
    if r.status != "ok":
        return False
    sol = parse_solution("solver", "", r.stdout)
    return bool(sol) and objective("vrptw", inst, sol)[0]


def label(row):
    if not row.get("code"):
        return "no_code"
    inst = gen("vrptw", row["n"], random.Random(row["key"]))
    stdin = describe("vrptw", inst)[1]
    if row["feasible"]:
        return "reads_service"
    head, rest = stdin.split("\n", 1)
    f = head.split()
    cf = " ".join(f[:3] + f[4:]) + "\n" + rest
    return "skips_service" if feasible_on(row["code"], inst, cf) else "other_fail"


def load(tag):
    p = f"{RES}/co_{tag}.jsonl"
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else None


def main():
    for prefix in sys.argv[1:]:
        runs = {s: load(f"{prefix}_s{s}") for s in (1, 2, 3)}
        runs = {s: r for s, r in runs.items() if r} or ({0: load(prefix)} if load(prefix) else {})
        if not runs:
            print(f"{prefix}: no files"); continue
        best = {}
        for s, rows in runs.items():
            with ThreadPoolExecutor(16) as ex:
                labs = list(ex.map(label, rows))
            n = len(rows); opt = sum(r["feasible"] and r["gap"] is not None and abs(r["gap"]) < 1e-9 for r in rows)
            feas = sum(bool(r["feasible"]) for r in rows); tok = sum(r["out_tokens"] for r in rows) / n
            cnt = {k: labs.count(k) for k in ("reads_service", "skips_service", "other_fail", "no_code")}
            print(f"{prefix}{'' if s == 0 else f'_s{s}':4s} opt {opt}/{n} ({opt / n:.2f})  feas {feas}/{n}  tokens {tok:.0f}  {cnt}")
            for r in rows:
                if r["feasible"] and (r["key"] not in best or r["value"] < best[r["key"]]["value"]):
                    best[r["key"]] = r
        if len(runs) > 1:
            n = len(next(iter(runs.values())))
            bo = sum(abs(r["gap"]) < 1e-9 for r in best.values())
            print(f"{prefix} best-of-{len(runs)} (label-free min objective): {bo}/{n} ({bo / n:.2f})")


if __name__ == "__main__":
    main()
