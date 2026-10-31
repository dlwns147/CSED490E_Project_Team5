"""VER (docs/prereg/PREREG_VER.md): score programs with a served verifier (poc/ver_build.py's prompt, thinking off): p_yes = P(yes) /
(P(yes) + P(no)) of the first answer token (case variants summed; 0.5 when neither is among the top 20). Scored: every passing program
(analyze_ho.ok_) of Qwen3-8B's stored word-problem arms formx (N), formxtb2000 (SB) and formxt (T), seeds 1-3, on OptiBench's third /
BWOR / LogiOR / OptMATH, and the train-dev programs (ver_dev_<name>.jsonl). Rows: results/x3/ver_<vtag>_<set>_<arm>_s<seed>.jsonl and
results/x3/ver_<vtag>_dev.jsonl = {id, [arm, right,] p_yes, in_tok}. Resumes.
usage: POC_BASE_URL=... python ver_score.py <vtag> <data name>"""
import contextlib, io, json, math, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from analyze_ho import ok_  # noqa: E402   (its import prints a report)
from run_nlopt import RES, _rows, problems  # noqa: E402
from ver_build import prompt  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
SETS, ARMS = ("optibench", "bwor", "logior", "optmath"), ("formx", "formxtb2000", "formxt")


def main():
    from llm import client
    vtag, name = sys.argv[1], sys.argv[2]

    def score(p):
        try:
            return _score(p)
        except Exception as e:
            print(vtag, "request failed, no row:", repr(e)[:200], flush=True)

    def _score(p):
        r = client.completions.create(model="local", prompt=f"<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n",
                                      max_tokens=1, temperature=0.0, logprobs=20)
        top = r.choices[0].logprobs.top_logprobs[0] or {}
        y = sum(math.exp(v) for k, v in top.items() if k.strip().lower() == "yes")
        n = sum(math.exp(v) for k, v in top.items() if k.strip().lower() == "no")
        return {"p_yes": y / (y + n) if y + n > 0 else 0.5, "in_tok": r.usage.prompt_tokens}

    jobs = []   # (path, row without score, prompt)
    for b in SETS:
        Q = {p["id"]: p["q"] for p in problems(b)}
        keep = {r["id"] for s in (1, 2, 3) for r in _rows(f"{RES}/opt_q8b_{b}_formxt_s{s}.jsonl")}   # OptiBench: its third
        for a in ARMS:
            for s in (1, 2, 3):
                path = f"{RES}/ver_{vtag}_{b}_{a}_s{s}.jsonl"
                done = {r["id"] for r in _rows(path)}
                jobs += [(path, {"id": r["id"]}, prompt(Q[r["id"]], r["code"], r["pred"]))
                         for r in _rows(f"{RES}/opt_q8b_{b}_{a}_s{s}.jsonl") if r["id"] in keep and ok_(r) and r["id"] not in done]
    path = f"{RES}/ver_{vtag}_dev.jsonl"
    done = {(r["id"], r["prompt_hash"]) for r in _rows(path)}
    jobs += [(path, {"id": x["id"], "arm": x["arm"], "right": x["right"], "prompt_hash": zlib.crc32(x["prompt"].encode())}, x["prompt"])
             for x in map(json.loads, open(f"{DATA}/optmath_train/ver_dev_{name}.jsonl"))
             if (x["id"], zlib.crc32(x["prompt"].encode())) not in done]
    print(vtag, f"{len(jobs)} programs to score", flush=True)
    files = {}
    with ThreadPoolExecutor(int(os.environ.get("VER_THREADS", 64))) as ex:
        for (path, row, _), out in zip(jobs, ex.map(lambda j: score(j[2]), jobs)):
            if out is None:
                continue
            f = files.get(path) or files.setdefault(path, open(path, "a"))
            f.write(json.dumps({**row, **out}) + "\n"); f.flush()
    for f in files.values():
        f.close()
    print(vtag, "done", flush=True)


if __name__ == "__main__":
    main()
