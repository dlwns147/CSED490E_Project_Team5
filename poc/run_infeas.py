"""INFEAS (docs/prereg/PREREG_X7.md, 2026-10-19): a cheap repair for programs that report 'No Best Solution'. Stated word problems are
almost always feasible (MAMO: no infeasible label), so an infeasible model means a constraint was written more strictly than the text.
For every row of <src_mode> (seed s) whose program printed 'No Best Solution', one repair turn WITHOUT thinking: the original prompt, the
model's program, and a generic message (infeasible, the problem has a solution, find the over-strict constraint). The repaired program is
run and graded like run_nlopt.
usage: [NLOPT_SET=mamo] POC_BASE_URL=... python run_infeas.py <tag> <src_mode> <seed>   -> results/x3/opt_<tag>_<src_mode>r_s<seed>.jsonl"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, P_MIP, SNIP, problems, value_of, correct, _rows, _verified_examples  # noqa: E402

REPAIR = ("Running your program, the solver reported that the model has no feasible solution, so it printed `No Best Solution`. The problem "
          "as stated does have a feasible optimal solution, so at least one constraint in your program is stricter than what the text says. "
          "Re-read the problem sentence by sentence, find the constraint(s) you wrote more strictly than the text, and give the corrected "
          "complete program in a single ```python code block. It must print ONLY the optimal objective value.")


if __name__ == "__main__":
    from llm import chat_msgs, last_block
    from sandbox import run_python
    tag, src, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if src == "mips":
        os.environ["NLOPT_EX_SHORTEST"] = "1"
    EX = _verified_examples(os.environ.get("NLOPT_EX_TAG", tag)) if src == "mips" else None
    P = {p["id"]: p for p in problems()}
    todo = [r for r in _rows(f"{RES}/opt_{tag}_{src}_s{seed}.jsonl") if r.get("pred") == "NBS" and r.get("code")]
    path = f"{RES}/opt_{tag}_{src}r_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}

    def one(r):
        p = P[r["id"]]
        q = (P_MIP + SNIP if src == "mipf" else P_MIP).format(q=p["q"])
        if EX:
            ex = EX(p)
            if ex:   # the same mined example as the source run (run_nlopt mips)
                q += "\n\nA program that runs with this library (written for a different problem):\n```python\n" + ex.strip() + "\n```"
        msgs = [{"role": "user", "content": q}, {"role": "assistant", "content": f"```python\n{r['code']}\n```"},
                {"role": "user", "content": REPAIR}]
        o = chat_msgs(msgs, max_tokens=8192, temperature=0.7, seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997 + 7)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        res = run_python(code, "", timeout=60, mem_bytes=4 << 30) if code else None
        out = (res.stdout if res and res.status == "ok" else "") or ""
        lines = [l for l in out.strip().splitlines() if l.strip()]
        pred = value_of(lines[-1]) if lines else None
        return {"id": p["id"], "src": p["src"], "gold": p["gold"], "mode": src + "r", "out_tokens": o.get("out_tokens"), "finish": o.get("finish"),
                "code": code, "status": (res.status if res else "no_code"), "stdout": out[-300:], "err": ((res.stderr or "")[-300:] if res else ""),
                "pred": pred, "correct": correct(pred, p["gold"]), "first_code": r["code"]}
    with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, r) for r in todo if r["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = _rows(path)
    print(tag, src, seed, f"repaired {len(rows)}: correct {sum(r['correct'] for r in rows)}, still infeasible {sum(r['pred'] == 'NBS' for r in rows)}, "
          f"tokens {sum(r['out_tokens'] or 0 for r in rows) / max(1, len(rows)):.0f}", flush=True)
