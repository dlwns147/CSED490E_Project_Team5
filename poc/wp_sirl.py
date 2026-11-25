"""PREREG_DIFF addendum SIRL-B (2026-11-25): SIRL-Qwen2.5-32B-COPT (Chen et al., arXiv 2505.11792; a specialised, solver-informed-RL
optimisation-modelling model) as the recent-research baseline on our word-problem sets, run with its own recipe: the COPT prompt
template and the code / objective extractors of github.com/Cardinal-Operations/SIRL (rule_prompt_utils.py, utils.py; cloned to
$POC_DATA/optmath_train/sirl_dl/repo) and its reproduce_copt.ipynb decode: n = 1, temperature 0.5, top_p 0.9, repetition_penalty 1.02,
16,384 output tokens, the program run for <= 200 s. Grading: the project scorer (run_nlopt.correct) on the first run = PRIMARY (no gold
used). Their notebook's checker also re-runs the program with integer<->continuous variables swapped (utils.change_variable_types) when
the first objective mismatches the GOLD or is infeasible, and counts either: that is reported second, labelled 'their checker' (it
consults the gold, so it is an upper bound, not a deployable method).
The pip coptpy in the sandbox carries COPT's size-limited licence; a solve refused for size counts as wrong (stated in advance).
ORLM-B (same addendum family, 2026-11-25): ORLM-LLaMA-3-8B (Huang et al., Operations Research 2025; github.com/Cardinal-Operations/ORLM,
cloned to $POC_DATA/optmath_train/orlm_repo) with its own recipe: the README / eval/generate.py completion template (no chat template),
greedy decoding, the first ```python block, eval/execute.py's appended print of model.objval ("Just print the best solution:"), 600 s
per program. Deviation: 6,144 output tokens (theirs: up to the 8,192 context).
OPTIMIND-B (addendum CLEAN, 2026-11-25): microsoft/OptiMind-SFT (gpt-oss-20b fine-tune, arXiv 2509.22979) with its model card's system
prompt and user message = the problem; temperature 0.9, top_p 1.0 (the card's values), reasoning effort left at the template default, 30,000
output tokens (the card's example has 4,096, the paper 60,000; our server holds 34k); the last ```python block is run with model.optimize()
output, the objective printed by an appended line (the paper parses a tagged objective). Solver gurobipy (pip, size-limited licence).
usage: POC_BASE_URL=... python wp_sirl.py run <sirl|orlm|optimind> <set> <seed>   |   python wp_sirl.py score <sirl|orlm|optimind> <set>"""
import json, os, random, sys, zlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "optmath_train", "sirl_dl", "repo")
sys.path.insert(0, REPO)
R3 = f"{ROOT}/results/x3"


ORLM_T = ("Below is an operations research question. Build a mathematical model and corresponding python code using `coptpy` that "
          "appropriately addresses the question.\n\n# Question:\n{Question}\n\n# Response:")
ORLM_ADD = '\nif model.status == COPT.OPTIMAL:\n    print(f"Just print the best solution: {model.objval}")\nelse:\n    print("No Best Solution")'


def resume(out):
    """ids already answered; rows with zero output tokens are FAILED REQUESTS (prompt + output over the served context), not answers: they
    are removed from the file so the next run asks again (2026-11-25: 4 SIRL and 8 ORLM rows had been counted as wrong / no code)"""
    if not os.path.exists(out):
        return set()
    R = [json.loads(l) for l in open(out)]
    K = [r for r in R if int(r.get("out_tokens") or 0) > 0]
    if len(K) < len(R):
        with open(out, "w") as f:
            f.write("".join(json.dumps(r) + "\n" for r in K))
        print(f"re-asking {len(R) - len(K)} failed requests in {out}")
    return {r["id"] for r in K}


def run_orlm(st, seed):
    os.environ["NLOPT_SET"] = st
    import re
    import run_nlopt as RN
    import llm
    from sandbox import run_python
    P = RN.problems()
    out = f"{R3}/opt_orlm8_{st}_copt_s{seed}.jsonl"
    done = resume(out)

    def one(p):
        try:
            r0 = llm.client.completions.create(model="local", prompt=ORLM_T.replace("{Question}", p["q"].strip()), temperature=0, top_p=1,
                                               max_tokens=max(256, min(6144, 8192 - 8 - llm.n_tokens(ORLM_T.replace("{Question}", p["q"].strip())))), stop=["</s>"])
            text, ntok = r0.choices[0].text or "", r0.usage.completion_tokens
        except Exception as e:
            text, ntok = "", 0; print("request failed", p["id"], str(e)[:200])
        a = text.find("```python")
        code = text[a:text.find("```", a + 9)].replace("```python", "") if a >= 0 else ""
        r = run_python(code + ORLM_ADD, "", timeout=600, mem_bytes=8 << 30, cpu_s=4800) if code.strip() else None
        out_s = (r.stdout or "") if r else ""
        m = re.search(r"Just print the best solution:\s*(\S+)", out_s)
        try:
            pred = float(m.group(1)) if m else ("NBS" if "No Best Solution" in out_s else None)
        except ValueError:
            pred = None
        return {"id": p["id"], "gold": p["gold"], "out_tokens": ntok, "status": (r.status if r else "no_code"), "pred": pred,
                "infeasible": False, "pred2": None, "correct2": False, "stdout": out_s[-300:], "err": ((r.stderr or "")[-300:] if r else ""),
                "correct": RN.correct(pred, p["gold"]) if pred is not None else False}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for z in ex.map(one, [p for p in P if p["id"] not in done]):
            f.write(json.dumps(z) + "\n"); f.flush()


OM_SYS = """You are an expert in optimization and mixed integer programming. You are given an
optimization problem and you need to solve it using gurobipy.
Reason step by step before generating the gurobipy code.
When you respond, first think carefully.
After thinking, output the math modeling of the problem.
Finally output a ```python ...``` code block that solves the problem.
The code must include:
import gurobipy as gp
from gurobipy import GRB
"""
# the program runs unchanged under a subclass of gurobipy.Model that records each optimize() call's status / objective (the model may live
# inside a function, so globals cannot be read afterwards); the last recorded optimal objective is printed on exit as OMOBJ
OM_PRE = """
import atexit as _ax
import gurobipy as _gp
_REC = []
_Base = _gp.Model
class _RecModel(_Base):
    def optimize(self, *a, **k):
        r = super().optimize(*a, **k)
        try:
            _REC.append((int(self.Status), float(self.ObjVal) if self.SolCount > 0 else None))
        except Exception as _e:
            _REC.append((-1, None))
        return r
_gp.Model = _RecModel
def _out():
    ok = [o for s, o in _REC if s == 2 and o is not None]
    print("\\nOMOBJ:", ok[-1] if ok else ("none status %d" % _REC[-1][0] if _REC else "none status 0"), flush=True)
_ax.register(_out)
"""


def run_optimind(st, seed):
    os.environ["NLOPT_SET"] = st
    import re
    import run_nlopt as RN
    import llm
    from llm import last_block
    from sandbox import run_python
    P = RN.problems()
    out = f"{R3}/opt_optimind_{st}_gurobi_s{seed}.jsonl"
    done = resume(out)

    def one(p):
        try:
            r0 = llm.client.chat.completions.create(model="local", messages=[{"role": "system", "content": OM_SYS}, {"role": "user", "content": p["q"]}],
                                                    temperature=0.9, top_p=1.0, max_tokens=30000, seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
            text, ntok, fin = r0.choices[0].message.content or "", r0.usage.completion_tokens, r0.choices[0].finish_reason
        except Exception as e:
            text, ntok, fin = "", 0, "error"; print("request failed", p["id"], str(e)[:200])
        code = last_block(text, ("python", "py", "python3"))
        r = run_python(OM_PRE + code, "", timeout=200, mem_bytes=8 << 30, cpu_s=1600) if code else None
        so = (r.stdout or "") if r else ""
        m = re.findall(r"OMOBJ: (-?[0-9.eE+-]+)", so)
        pred = None
        if m:
            try:
                pred = float(m[-1])
            except ValueError:
                pred = None
        if pred is None and "OMOBJ: none status 3" in so:
            pred = "NBS"
        return {"id": p["id"], "gold": p["gold"], "out_tokens": ntok, "finish": fin, "status": (r.status if r else "no_code"), "pred": pred,
                "pred2": None, "correct2": False, "infeasible": False, "code": code, "stdout": so[-300:], "err": ((r.stderr or "")[-300:] if r else ""),
                "correct": RN.correct(pred, p["gold"]) if pred is not None else False}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for z in ex.map(one, [p for p in P if p["id"] not in done]):
            f.write(json.dumps(z) + "\n"); f.flush()


def run(st, seed):
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    import llm
    from sandbox import run_python
    from rule_prompt_utils import copt_prompt_temp
    from utils import extract_code_block, extract_obj, change_variable_types
    P = RN.problems()
    out = f"{R3}/opt_sirl32_{st}_copt_s{seed}.jsonl"
    done = resume(out)

    def one(p):
        msgs = [{"role": k, "content": copt_prompt_temp[k].replace("{question}", p["q"]).strip()} for k in ("system", "user")]
        try:
            r0 = llm.client.chat.completions.create(model="local", messages=msgs, temperature=0.5, top_p=0.9, max_tokens=16384,
                                                    seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997, extra_body={"repetition_penalty": 1.02})
            text, ntok = r0.choices[0].message.content or "", r0.usage.completion_tokens
        except Exception as e:   # a failed request is a wrong answer at zero tokens, recorded
            text, ntok = "", 0; print("request failed", p["id"], str(e)[:200])
        code = extract_code_block(text, "copt")
        ex = lambda c: run_python(c, "", timeout=200, mem_bytes=8 << 30, cpu_s=1600)
        r = ex(code) if code else None
        pred = extract_obj((r.stdout or "") if r else "", "copt")
        if pred is None and r and "nfeasible" in (r.stdout or ""):
            pred = "NBS"   # gold 'No Best Solution' (BWOR's two infeasible problems)
        alt = change_variable_types(text) if code else None   # their checker's second run (scored separately, see docstring)
        c2 = extract_code_block(alt, "copt") if alt else None
        r2 = ex(c2) if c2 and c2 != code else None
        pred2 = extract_obj((r2.stdout or "") if r2 else "", "copt")
        return {"id": p["id"], "gold": p["gold"], "out_tokens": ntok, "status": (r.status if r else "no_code"),
                "pred": pred, "pred2": pred2, "infeasible": bool(r and "nfeasible" in (r.stdout or "")),
                "stdout": ((r.stdout or "")[-300:] if r else ""), "err": ((r.stderr or "")[-300:] if r else ""),
                "correct": RN.correct(pred, p["gold"]) if pred is not None else False,
                "correct2": RN.correct(pred2, p["gold"]) if pred2 is not None else False}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for z in ex.map(one, [p for p in P if p["id"] not in done]):
            f.write(json.dumps(z) + "\n"); f.flush()


def score(mdl, st):
    tag = {"sirl": "sirl32", "orlm": "orlm8", "optimind": "optimind"}[mdl]
    rows = [json.loads(l) for f in sorted(os.listdir(R3)) if f.startswith((f"opt_{tag}_{st}_copt_s", f"opt_{tag}_{st}_gurobi_s")) for l in open(f"{R3}/{f}")]
    n = len(rows)
    lic = sum("exceed" in (r.get("stdout", "") + r.get("err", "")).lower() for r in rows)   # COPT size limit (its banner always says "licen")
    their = sum(r["correct"] or ((r["infeasible"] or r["pred"] is not None) and r.get("correct2")) for r in rows)
    print(f"{st}: {tag} their checker (uses gold, upper bound) {100*their/max(1,n):.1f}%")
    print(f"{st}: {tag} n={n} accuracy {100*sum(r['correct'] for r in rows)/max(1,n):.1f}%  tokens "
          f"{sum(int(r.get('out_tokens') or 0) for r in rows)/max(1,n):.0f}  utility "
          f"{sum(100*r['correct'] - 0.5*int(r.get('out_tokens') or 0)/1000 for r in rows)/max(1,n):.2f}  no code {sum(r['status']=='no_code' for r in rows)}  "
          f"licence-limited {lic}")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        {"sirl": run, "orlm": run_orlm, "optimind": run_optimind}[sys.argv[2]](sys.argv[3], int(sys.argv[4]))
    else:
        score(sys.argv[2], sys.argv[3])
