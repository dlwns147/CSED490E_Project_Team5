"""HO6 (docs/prereg/PREREG_HO.md): one cheap repair turn (no thinking) with the failure evidence, before thinking. For every freev program
that does not run, prints nothing or 'No Best Solution', or whose solution the HO3 checker (verify_*) does not pass, the same model gets
the problem, its program and the evidence, and writes a corrected program in the freev format; it is run as freev programs are.
usage: NLOPT_SET=bwor POC_BASE_URL=... python run_repair.py <model> <seed> [arm]   -> results/x3/repair_<model>_<set>[_<arm>]_s<seed>.jsonl
arm (HO7): freev (default; with the HO3 checker's verdicts) or a solver-choice arm without a checker (free, formx): only visible failures
(no run, no value, 'No Best Solution') are repaired, and the corrected program prints the objective alone on its last line."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, P_FREE, P_FREEV, _rows, correct, problems, value_of  # noqa: E402

ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")

FIX = """{task}

Your previous program:
```python
{code}
```
{evidence}

Write the corrected complete program ({fmt}; `No Best Solution` only if the problem truly has no optimal solution). Give it in a single
```python code block."""
FMT_V = "same output format: the JSON line of the decision variable values, then the optimal objective value alone on the last line"
FMT_F = "same output format: the optimal objective value alone on the last line"


def evidence(f, v):
    if f.get("status") != "ok":
        tail = "\n".join((f.get("err") or "").strip().splitlines()[-4:])
        return f"Running it failed with:\n```\n{tail or f.get('status')}\n```"
    if f.get("pred") is None:
        return "It ran but printed no objective value."
    if f.get("pred") == "NBS":
        return "It printed `No Best Solution`, but the problem is expected to have an optimal solution; check the constraints and data."
    if v and v.get("verdict", "").startswith("VIOLATION"):
        return f"A check of its printed solution against the problem's constraints reported: {v['verdict']}"
    if v and v.get("verdict", "").startswith("OK"):
        return f"A check that recomputed the objective from its printed solution got {v.get('checker_value')}, not the printed {f.get('pred')}."
    return "A check of its printed solution against the problem's constraints did not pass."


def main():
    from llm import chat, last_block
    from sandbox import run_python
    m, seed = sys.argv[1], int(sys.argv[2])
    SET = os.environ.get("NLOPT_SET", "bwor")
    Q = {p["id"]: p for p in problems(SET)}
    arm = sys.argv[3] if len(sys.argv) > 3 else "freev"
    F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{SET}_{arm}_s{seed}.jsonl")}
    V = {r["id"]: r for r in _rows(f"{RES}/verify_{m}_{SET}_s{seed}.jsonl")} if arm == "freev" else {}
    path = f"{RES}/repair_{m}_{SET}{'' if arm == 'freev' else '_' + arm}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    if arm == "freev":
        todo = [f for i, f in F.items() if i not in done and f.get("code") and not (ok_(f) and V.get(i, {}).get("passed"))]
    else:   # HO7: visible failures only
        todo = [f for i, f in F.items() if i not in done and f.get("code") and not ok_(f)]

    def one(f):
        task = (P_FREEV if arm == "freev" else P_FREE).format(q=Q[f["id"]]["q"])
        o = chat(FIX.format(task=task, code=f["code"].strip(), evidence=evidence(f, V.get(f["id"])), fmt=FMT_V if arm == "freev" else FMT_F),
                 max_tokens=8192, temperature=0.7,
                 seed=seed * 1000 + zlib.crc32(f["id"].encode()) % 997 + 23)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        r = run_python(code, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600) if code else None
        out = (r.stdout if r and r.status == "ok" else "") or ""
        lines = [l for l in out.strip().splitlines() if l.strip()]
        pred = value_of(lines[-1]) if lines else None
        return {"id": f["id"], "gold": f["gold"], "status": (r.status if r else "no_code"), "pred": pred, "correct": correct(pred, f["gold"]),
                "code": code, "err": ((r.stderr or "")[-300:] if r else ""), "evidence": evidence(f, V.get(f["id"]))[:300],
                "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as fh:
        for fu in as_completed([ex.submit(one, f) for f in todo]):
            fh.write(json.dumps(fu.result()) + "\n"); fh.flush()
    R = _rows(path)
    print(m, SET, seed, f"repaired {len(R)}: run and print a value {sum(ok_(r) for r in R)}", flush=True)


if __name__ == "__main__":
    main()
