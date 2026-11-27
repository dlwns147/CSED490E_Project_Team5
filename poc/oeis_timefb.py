"""TIME-FB (PREREG_DIFF, 2026-11-27): the OEIS native-tool attempt (tir_native's prompt and harness, unchanged) with a runtime check of its final
program: the harness runs the final program for the graded indices (offset .. offset+19) under the grading limit (4 s per term) and returns ONLY
which indices timed out, crashed or printed nothing — never a value — to the same session (at most FB_TRIES times); the last final program is graded.
Why: 66 of 927 stored tool attempts (37 sequences) are right on every term they finish and fail only by timing out; the prompt says "a short period".
usage: POC_BASE_URL=... python oeis_timefb.py <seed> -> results/x44/tirtf_oeisf_medium_s<seed>.jsonl
Temporary files: each session's sandbox is removed by Session.close(); run_python cleans its own temporary files."""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
from tir_dispute import Session
import run_compute as RC
R = T.R; FB_TRIES = int(os.environ.get("FB_TRIES", 2))
MSG = ("The grader runs your final program once for each n = {lo}, ..., {hi} with a limit of {s} seconds per n. Your program did not finish within the limit "
       "for n = {tle}{err}. Make it fast enough for every one of these n (you can time it in the python tool), keep it correct, and output the complete program "
       "again at the end inside triple backticks.")


def statuses(code, off):
    bad, err = [], []
    for i in range(RC.NTERMS):
        r = RC.run_python(code, str(off + i), timeout=RC.TERM_S, mem_bytes=2 << 30)
        if r.status == "tle":
            bad.append(off + i)
        elif r.status != "ok" or not (r.stdout or "").strip():
            err.append(off + i)
    return bad, err


def solve(p, prompt, seed):
    import llm
    from llm import last_block
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    off = int(str(p["offset"]).split(",")[0]); s = Session(prompt(p), "medium", seed, tok); log = []
    try:
        fin = s.gen(T.CAP); final = fin
        for _ in range(FB_TRIES):
            code = last_block(final or "", ("python", "py", "python3", ""))
            if not code or s.fin != "stop":
                break
            bad, err = statuses(code, off); log.append({"tle": bad, "err": err})
            if not bad and not err:
                break
            m = MSG.format(lo=off, hi=off + RC.NTERMS - 1, s=RC.TERM_S, tle=", ".join(map(str, bad)) if bad else "(none)",
                           err=(" and it crashed or printed nothing for n = " + ", ".join(map(str, err))) if err else "")
            f2 = s.ask(m, T.CAP - s.used)
            if f2:
                final = f2
            else:
                break
    finally:
        s.close()
    return {"final": final or "", "out_tokens": s.used, "calls": s.calls, "finish": s.fin, "fb": log}


def main(seed):
    P, prompt, grade = T.task("oeisf"); path = f"{R}/tirtf_oeisf_medium_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            z = solve(p, prompt, seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "fb": []}
        z.update(id=p["id"], **grade(p, z["final"])); z["final"] = z["final"][-4000:]; z.pop("outs_", None); return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 32))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            f.write(json.dumps(fu.result(), default=str) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"TIME-FB s{seed}: {100*sum(str(z['correct']) == 'True' for z in Z)/len(Z):.1f}% of {len(Z)} @ {sum(z['out_tokens'] for z in Z)/len(Z)/1000:.2f}k; feedback used {sum(bool(z['fb']) and bool(z['fb'][0]['tle'] or z['fb'][0]['err']) for z in Z)}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
