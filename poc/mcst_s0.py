"""MCST-A (PREREG_DIFF, 2026-11-28): attribution ablation of OWN-EF on MathConstraint. S0-F = OWN-EF with ONLY the own-check sentence (TS.OWN)
removed: same native tool, installed-solver sentence, answer-format sentence, submit(s) interface and format-only check at submit. Same seeds as
ONE (1, 2), so S0-F − ONE isolates the instruction to write and run a check of every stated condition before submitting; S0-F − TIR2 (lenient)
isolates the submit interface + format check.
usage: TIR_ENV=1 POC_BASE_URL=... python mcst_s0.py <seed> -> results/x44/mcst_S0F_s<seed>.jsonl
Temporary files: each attempt's sandbox is removed by Tool.close() in mcst_run.solve_own (finally block)."""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcst_run as M
M.TS.OWN = ""                       # the one change


def main(seed):
    path = f"{M.R}/mcst_S0F_s{seed}.jsonl"; done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            z = M.solve_own(p["prompt"], "medium", seed * 1000 + zlib.crc32(p["name"].encode()) % 997)
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200]}
        z["id"] = p["name"]; z["final"] = (z.get("final") or "")[-6000:]; z["codes"] = [c[:3000] for c in z.get("codes", [])]; z["outs"] = [o[:300] for o in z.get("outs", [])]
        return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in M.problems() if p["name"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"MCST S0F s{seed}: {len(Z)} rows @ {sum(z['out_tokens'] for z in Z)/len(Z)/1000:.2f}k", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
