"""Official-artifact baseline (CRITIQUE PLAN P2, 2026-11-20): LLMOPT (Jiang et al., ICLR 2025) with its released checkpoint
ant-opt/LLMOPT-Qwen2.5-14B and the prompts of its official repository (github.com/antgroup/LLMOPT, MIT licence: prompts/generate_prompt.py,
prompts/self_correction_prompt.py, inference/inference_q2f2c.py), served by vLLM.

Pipeline per problem (the repository's inference_q2f2c.py, plus the self-correction loop the paper describes; the repository ships the
self-correction prompt but not the loop): Q2F -> five-element model; F2C -> Pyomo code; run; the model judges five-element and code with
the self-correction prompt; a False regenerates that part (five-element False: both), up to MAX_ROUNDS generations; the objective is read
from the run's output by objective_of (the last line naming an objective); the repository's id_gt prompt also runs and is stored as
pred_idgt (11-20: on the first rows it often returned a decision variable, the first number printed). Every token of every call is counted.
Sandbox: Pyomo with HiGHS; a solver the sandbox lacks (glpk, cbc, gurobi, ...) is served by HiGHS at MIP gap 0 (sitecustomize shim in
the POC_PYTHON venv, see host notes), so a correct model is never lost to a missing binary.
LLMOPT's release excludes MAMO EasyLP / ComplexLP from training; the other sets may overlap its training data (stated in the record).

usage: POC_PYTHON=<pyomo venv python> run_llmopt.py <tag> <seed> <set,set,...>   -> results/x3/llmopt_<tag>_s<seed>.jsonl
"""
import json
import os
import re
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs  # noqa: E402
from sandbox import run_python  # noqa: E402
import run_nlopt as RN  # noqa: E402

MAX_ROUNDS = 12   # generations per problem; the paper reports average solving times up to 4.06 (OptMath), so the cap rarely binds

from llmopt_prompts import Q2F, F2C, id_gt, self_correction  # noqa: E402  (verbatim official prompts)


def clean(r):   # inference_q2f2c.py's post-processing
    return r.replace("\\\\n", "\n").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("\\\\\"", "\"")


def five_of(r):
    r = clean(r)
    for fence in ("```text", "```plaintext"):
        if fence in r:
            return r.split(fence)[1].split("```")[0]
    return r.split("```")[1].split("```")[0] if "```" in r else None


def code_of(r):
    r = clean(r)
    if "```python" not in r:
        return None
    return r.split("```python")[1].split("```")[0].replace('print("\\\\\n', 'print("').replace('print(f"\\\\\n', 'print(f"')


OBJ = re.compile(r"objective|total|optimal value|minim|maxim|cost|profit|revenue|value of", re.I)


def objective_of(out):
    """the objective printed by the program: the last number on the last line that names an objective (Pyomo code from this pipeline
    prints the solution and then the objective); else the last number printed. Deterministic, same rule for every row."""
    lines = [l for l in out.splitlines() if re.search(r"\d", l)]
    named = [l for l in lines if OBJ.search(l)]
    return RN.value_of((named or lines or [""])[-1])


def main():
    tag, seed, sets = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(",")
    P = [p for w in sets for p in RN.problems(w)]

    def ask(content, sd, tok):
        o = chat_msgs([{"role": "user", "content": content}], max_tokens=8192, temperature=0.7, seed=sd)
        tok[0] += o["out_tokens"]; tok[1] += o["in_tokens"]
        return o["text"] or ""

    def run(p):
        sd = seed * 10007 + zlib.crc32(p["id"].encode()) % 100000
        tok = [0, 0]; rounds = []; five = code = None; out = err = ""; regen = "five"
        for k in range(MAX_ROUNDS):
            if regen == "five" or not five:
                five = five_of(ask(Q2F(p["q"]), sd + 100 * k, tok))
            if five:
                code = code_of(ask(F2C(five), sd + 100 * k + 1, tok))
            if code:
                res = run_python(code, "", timeout=120, mem_bytes=2 << 30)
                out, err = res.stdout[-3000:], res.stderr[-1500:]
            else:
                out, err = "", "no code" if five else "no five-element"
            judge = ask(self_correction(p["q"], five or "", code or "", out, err), sd + 100 * k + 2, tok) if code else ""
            jf = re.search(r"five-element is\s*\**\s*(True|False)", judge, re.I); jc = re.search(r"code is\s*\**\s*(True|False)", judge, re.I)
            fok = bool(jf and jf.group(1).lower() == "true"); cok = bool(jc and jc.group(1).lower() == "true")
            rounds.append({"five_ok": fok, "code_ok": cok, "err": err[-300:], "out": out[-1500:], "code": (code or "")[-1500:], "judge": judge[-400:]})
            if code and fok and cok and not err.strip():
                break
            regen = "five" if not fok or not five else "code"
        val = vg = None
        if code and out.strip():
            v = ask(id_gt + out, sd + 9, tok).strip()   # the repository's id_gt step (kept as pred_idgt)
            vg = RN.value_of(v) if "nan" not in v.lower() else None
            val = objective_of(out)   # 11-20 first rows: id_gt often returned the first number printed (a decision variable)
            if val is None and re.search(r"infeasible|no (feasible|optimal) solution", out, re.I):
                val = vg = "NBS"
        try:
            ok = val is not None and RN.correct(val, p["gold"])
        except (TypeError, ValueError):
            ok = False
        return {"id": p["id"], "pred": val, "pred_idgt": vg, "gold": p["gold"], "correct": ok, "tokens": tok[0], "in_tokens": tok[1],
                "rounds": rounds, "n_rounds": len(rounds)}

    path = os.path.join(RN.RES, f"llmopt_{tag}_s{seed}.jsonl")
    with ThreadPoolExecutor(48) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, seed, f"{len(rows)} rows, answered {sum(r['pred'] is not None for r in rows)}, tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}, rounds {sum(r['n_rounds'] for r in rows) / len(rows):.2f}")


if __name__ == "__main__":
    main()
