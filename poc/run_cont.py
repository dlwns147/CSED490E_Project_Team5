"""CONT (docs/prereg/PREREG_CONT.md): where to stop a think, and whether to continue it after a failed check, on the four held-out
word-problem sets. Per problem and seed: formx's prompt (run_form.py, the same similar-problem program), the Qwen3 raw format and the
harness sampling of budget_chat (T 0.7, top-p 0.95: as the stored cut and full thinks of Qwen3-8B), one think of at most CAP tokens; then,
from that same think, the program forced at every EVERY thinking tokens inside it (budget_chat's cut: "Time is up; I will now write the
program." then </think>) and the program after the think's own end, as the stored full think (chat with 16,000 tokens in all: the
program gets what the think left, and a think that reaches CAP has none).
Every program runs and is graded as run_form's (60 s, 4 GB). The cut points are token counts of the think under the served tokenizer
(vLLM /tokenize, /detokenize). Rows: results/x3/cont_<tag>_<set>_s<seed>.jsonl = {id, gold, in_tok, think_tok, think_finish,
probes: [{at, tok, finish, status, pred, right}], end: {...}}; the think text goes to $POC_DATA/cont/<tag>_<set>_s<seed>.jsonl. Resumes.
usage: NLOPT_SET=<set> [FORM_SUBSET=0/3] [CONT_REVERSE=1] POC_BASE_URL=... python run_cont.py <tag> <seed> [--every 1000] [--cap 16000] [--ctx 24576]"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_form import SET, selector  # noqa: E402
from run_nlopt import RES, P_FREE, P_MIP, problems, value_of, correct, _rows  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
NOTE = "\n\nTime is up; I will now write the program.\n"


def arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    from llm import client, last_block, post_json
    from sandbox import run_python
    tag, seed = sys.argv[1], int(sys.argv[2])
    EVERY, CAP, CTX = arg("--every", 1000), arg("--cap", 16000), arg("--ctx", 24576)
    FREE = SET in ("optibench", "bwor", "logior")
    SEL = selector()
    P = problems()
    if os.environ.get("FORM_SUBSET"):
        i, k = map(int, os.environ["FORM_SUBSET"].split("/")); P = P[i::k]
    P = P[:int(os.environ.get("CONT_LIMIT", len(P)))]   # smoke only
    path = f"{RES}/cont_{tag}_{SET}_s{seed}.jsonl"
    os.makedirs(f"{DATA}/cont", exist_ok=True)
    tpath = f"{DATA}/cont/{tag}_{SET}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    main_path = path
    if os.environ.get("CONT_REVERSE"):   # a helper beside a running job: the problems in reverse order, its own files (analyses merge them)
        P = P[::-1]; path, tpath = path[:-6] + "_rev.jsonl", tpath[:-6] + "_rev.jsonl"
        done |= {r["id"] for r in _rows(path)}

    def grade(text, gold):
        code = last_block(text or "", ("python", "py", "python3"))
        res = run_python(code, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600 if FREE else None) if code else None
        lines = [l for l in ((res.stdout if res and res.status == "ok" else "") or "").strip().splitlines() if l.strip()]
        pred = value_of(lines[-1]) if lines else None
        return {"status": res.status if res else "no_code", "pred": pred, "right": correct(pred, gold)}

    def answer(prompt, n_in, sd, gold, mt=8192):
        mt = min(mt, CTX - n_in - 16)
        if mt < 256:
            return {"tok": 0, "finish": "no_room", "status": "no_code", "pred": None, "right": False}
        r = client.completions.create(model="local", prompt=prompt, max_tokens=mt, temperature=0.7, top_p=0.95, seed=sd, stop=["<|im_end|>"])
        return {"tok": r.usage.completion_tokens, "finish": r.choices[0].finish_reason, **grade(r.choices[0].text, gold)}

    def one(p):
        if path != main_path and p["id"] in {r["id"] for r in _rows(main_path)}:
            return None                     # the helper met the main job
        q = (P_FREE if FREE else P_MIP).format(q=p["q"])
        s = SEL(p)
        if s:
            q += ("\n\nA program for a similar problem (two independent runs of it agree and its model is feasible):\n```python\n"
                  + s[1][1].strip() + "\n```")
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997   # run_form's per-problem seed
        head = f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n<think>\n"
        r = client.completions.create(model="local", prompt=head, max_tokens=CAP, temperature=0.7, top_p=0.95, seed=sd, stop=["</think>"])
        think, n_in, fin = r.choices[0].text, r.usage.prompt_tokens, r.choices[0].finish_reason
        toks = post_json("/tokenize", {"model": "local", "prompt": think, "add_special_tokens": False})["tokens"]
        probes = []
        for c in range(EVERY, len(toks), EVERY):
            pre = post_json("/detokenize", {"model": "local", "tokens": toks[:c]})["prompt"]
            probes.append({"at": c, **answer(head + pre + NOTE + "\n</think>\n\n", n_in + c + 24, sd + c, p["gold"])})
        # the end as the stored full think (chat, 16,000 tokens in all): the program gets what the think left; a think that reaches the
        # cap has no program
        n_t = r.usage.completion_tokens
        end = (answer(head + think + "\n</think>\n\n", n_in + n_t + 8, sd, p["gold"], mt=CAP - n_t) if fin == "stop" and CAP - n_t >= 256 else
               {"tok": 0, "finish": "cap", "status": "no_code", "pred": None, "right": False})
        return ({"id": p["id"], "gold": p["gold"], "in_tok": n_in, "think_tok": r.usage.completion_tokens, "think_finish": fin,
                 "probes": probes, "end": end}, {"id": p["id"], "think": think})

    with ThreadPoolExecutor(int(os.environ.get("CONT_THREADS", 32))) as ex, open(path, "a") as f, open(tpath, "a") as g:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            try:
                if fu.result() is None:
                    continue
                row, txt = fu.result()
                g.write(json.dumps(txt) + "\n"); g.flush()
                f.write(json.dumps(row) + "\n"); f.flush()
            except Exception as e:
                print(tag, SET, seed, "request failed, no row:", repr(e)[:200], flush=True)
    R = _rows(path)
    print(tag, SET, seed, f"{len(R)} problems: end right {sum(r['end']['right'] for r in R)}, think {sum(r['think_tok'] for r in R) / max(1, len(R)):.0f} "
          f"tokens, probes {sum(len(r['probes']) for r in R) / max(1, len(R)):.1f}", flush=True)


if __name__ == "__main__":
    main()
