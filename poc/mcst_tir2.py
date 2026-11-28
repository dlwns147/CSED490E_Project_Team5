"""MCST TIR2 (PREREG_DIFF addendum MCST, amendment 2026-11-28 12:32 UTC): the plain native-tool baseline again, keeping the raw final message.
mcst_run.py's TIR arm kept only the \\boxed{} content and stored "" when there was no box (65 of 329 seed-1 finals), so a reader that also takes the last
JSON list / the word UNSATISFIABLE from the message (mcst_grade.py, lenient reading) could not be applied. Same prompt, seeds and settings as TIR.
usage: TIR_ENV=1 POC_BASE_URL=... python mcst_tir2.py <seed> -> results/x44/mcst_TIR2_s<seed>.jsonl (final = box content, raw = final message)
Temporary files: each attempt's sandbox is removed by Tool.close() inside tir_native.solve."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcst_run as M
T = M.T


def main(seed):
    path = f"{M.R}/mcst_TIR2_s{seed}.jsonl"; done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            z = T.solve(p["prompt"] + M.FMT + "\n\nPut the final answer alone in \\boxed{}.", "medium", seed * 1000 + zlib.crc32(p["name"].encode()) % 997)
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "codes": [], "outs": []}
        raw = z.get("final") or ""; b = re.findall(r"\\boxed\{(.*)\}", raw, re.S)
        z.update(id=p["name"], final=(b[-1] if b else "")[-6000:], raw=raw[-6000:], codes=[c[:3000] for c in z.get("codes", [])], outs=[o[:300] for o in z.get("outs", [])])
        return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in M.problems() if p["name"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"MCST TIR2 s{seed}: {len(Z)} rows @ {sum(z['out_tokens'] for z in Z)/len(Z)/1000:.2f}k; no box {sum(not z['final'] for z in Z)}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
