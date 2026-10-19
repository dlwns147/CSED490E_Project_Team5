"""ADAPT (docs/prereg/PREREG_X1.md, addendum 2026-10-19): a learned when-to-think switch vs our label-free gate, same backbone, same problems.
Models: DeepSeek-R1-Distill-Qwen-7B (tag r1d7) and AdaptThink-7B-delta0.05 (tag adt7: the same model after RL that teaches it to skip
thinking on easy problems; Zhang et al. 2025, arXiv 2505.13417). The model card's chat template ends in "<think>\\n"; the paper's NoThinking
mode is a response whose first token is "</think>", so the cheap modes prefill "</think>".
Modes: think = the template as is (r1d7 always thinks; adt7 chooses), text = NoThinking text, prog = NoThinking Python program (run, 30 s).
Settings as in the paper: T 0.6, top_p 0.95, 16K context (max_tokens = 16384 - prompt), DeepScaleR's instruction for text / think.
usage: POC_BASE_URL=... python run_adapt.py <tag> <mode> <seed>   -> results/x1/math_<tag>_<mode>_s<seed>.jsonl (graded like run_math)"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import last_block  # noqa: E402
from run_math import RES, PROG, problems, regrade, to_candidates, _rows  # noqa: E402
from sandbox import run_python  # noqa: E402

TEXT = "{p} Let's think step by step and output the final answer within \\boxed{{}}."   # DeepScaleR / AdaptThink training prompt
CTX = 16384


def prompt(q, mode):
    # BOS is added by the server's tokenizer (add_bos_token = true), so it is not written here
    return "<｜User｜>" + (PROG if mode == "prog" else TEXT).format(p=q) + "<｜Assistant｜><think>\n" + ("</think>" if mode != "think" else "")


if __name__ == "__main__":
    from openai import OpenAI
    tag, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    client = OpenAI(base_url=os.environ["POC_BASE_URL"], api_key="none", timeout=3600)
    path = f"{RES}/math_{tag}_{mode}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}

    def one(p):
        pr = prompt(p["problem"], mode)
        r = client.completions.create(model="local", prompt=pr, max_tokens=CTX - 1024, temperature=0.6,   # prompts are < 1k tokens
                                      top_p=0.95, seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        raw = r.choices[0].text or ""
        fin = r.choices[0].finish_reason
        if mode == "think":
            nothink = raw.lstrip().startswith("</think>")
            text = raw.split("</think>", 1)[1] if "</think>" in raw else ("" if fin == "length" else raw)
        else:
            nothink, text = True, raw
        row = {"id": p["id"], "src": p["src"], "level": p["level"], "subject": p["subject"], "gold": p["answer"], "mode": mode,
               "out_tokens": r.usage.completion_tokens, "finish": fin, "nothink": nothink}
        if mode == "prog":
            code = last_block(text, ("python", "py", "python3"))
            res = run_python(code, "", timeout=30, mem_bytes=2 << 30) if code else None
            out = (res.stdout if res and res.status == "ok" else "") or ""
            row.update(code=code, status=(res.status if res else "no_code"), stdout=out[-500:], cands=to_candidates(out),
                       raw=text[-1500:] if not code else "")   # 2026-10-19: keep the reply when no program was found (audit)
        else:
            row.update(text=text[-3000:], head=raw[:300])
        return row
    with ThreadPoolExecutor(96) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in problems() if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = regrade(path)
    by = {}
    for r in rows:
        by.setdefault(r["src"], []).append(r["correct"])
    print(tag, mode, seed, {k: f"{sum(v)}/{len(v)}" for k, v in by.items()}, f"tokens {sum(r['out_tokens'] or 0 for r in rows) / len(rows):.0f}",
          f"nothink {sum(r['nothink'] for r in rows)}/{len(rows)}", flush=True)
