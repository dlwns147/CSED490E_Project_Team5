"""Input tokens of the held-out policies (review 2026-10-22, docs/notes/CRITIQUE.md item 4): every cost so far counted output tokens only,
but the library arm (formx) pastes a whole program into the prompt. Rebuilds each arm's exact user prompt (the library program selected
for each problem as run_form.py does), counts it with the model's own tokenizer (chat-template tokens not included: a constant per call)
and reports, per policy, input and output tokens per problem and the policy's total relative to always thinking.
usage: python analyze_input_tokens.py [set ...]   (sets: optmath optibench bwor logior; runs on the login node, OR-Tools stubbed)"""
import importlib, json, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import ortools.linear_solver.pywraplp  # noqa: F401
except ImportError:   # login node: run_nlopt builds an unused card from pywraplp at import time
    o, ls = types.ModuleType("ortools"), types.ModuleType("ortools.linear_solver")
    ls.pywraplp = types.SimpleNamespace(**{c: type(c, (), {}) for c in ("Solver", "Variable", "Constraint", "Objective")})
    o.linear_solver = ls
    sys.modules.update({"ortools": o, "ortools.linear_solver": ls, "ortools.linear_solver.pywraplp": ls.pywraplp})
from tokenizers import Tokenizer  # noqa: E402

MODELS = os.environ.get("MODELS_DIR", "/home/leesangjun/SSD/huggingface")
TOK = {"oss20": f"{MODELS}/openai/gpt-oss-20b/tokenizer.json", "q14a": f"{MODELS}/Qwen/Qwen3-8B/tokenizer.json",
       "q8b": f"{MODELS}/Qwen/Qwen3-8B/tokenizer.json"}   # Qwen3-14B-AWQ uses the same Qwen3 vocabulary
ARMS = {"optmath": ("mips", "thinks", "formx"), "optibench": ("free", "thinkfree", "formx"), "bwor": ("free", "thinkfree", "formx"),
        "logior": ("free", "thinkfree", "formx")}


def main():
    for SET in sys.argv[1:] or list(ARMS):
        os.environ["NLOPT_SET"] = SET
        for mod in ("run_nlopt", "run_form"):
            sys.modules.pop(mod, None)
        R = importlib.import_module("run_nlopt"); F = importlib.import_module("run_form")
        P = {p["id"]: p for p in R.problems(SET)}
        sel = F.selector()
        cheap, think, lib = ARMS[SET]
        free = SET != "optmath"
        print(f"=== {SET} ({len(P)} problems; cheap arm {cheap}, thinking {think}, library formx)")
        for m in ("oss20", "q14a", "q8b"):
            tk = Tokenizer.from_file(TOK[m]); n = lambda t: len(tk.encode(t).ids)
            os.environ["NLOPT_EX_SHORTEST"] = "1"
            EX = R._verified_examples(m) if not free else None
            base = {i: (R.P_FREE if free else R.P_MIP).format(q=p["q"]) for i, p in P.items()}
            def with_ex(i):   # the automatic usage example of mips / thinks (OptMATH)
                ex = EX(P[i]) if EX else None
                return base[i] + ("\n\nA program that runs with this library (written for a different problem):\n```python\n" + ex.strip() + "\n```" if ex else "")
            def with_lib(i):
                s = sel(P[i])
                return base[i] + ("\n\nA program for a similar problem (two independent runs of it agree and its model is feasible):\n```python\n"
                                  + s[1][1].strip() + "\n```" if s else "")
            prompt = {cheap: (with_ex if not free else base.__getitem__), think: (with_ex if not free else base.__getitem__), lib: with_lib}
            inp = {a: {i: n(f(i)) for i in P} for a, f in prompt.items()}
            ok_ = lambda r: r["status"] == "ok" and r.get("pred") not in (None, "NBS")
            for c in (cheap, lib):
                tot = {k: [0, 0] for k in ("CHEAP", "FF", "THINK")}; cnt = 0
                for s in (1, 2, 3):
                    Fr, T = R._rows(f"{R.RES}/opt_{m}_{SET}_{c}_s{s}.jsonl"), R._rows(f"{R.RES}/opt_{m}_{SET}_{think}_s{s}.jsonl")
                    Fr, T = {r["id"]: r for r in Fr}, {r["id"]: r for r in T}
                    for i, f in Fr.items():
                        if i not in T:
                            continue
                        cnt += 1; t = T[i]; esc = not ok_(f)
                        tot["CHEAP"][0] += inp[c][i]; tot["CHEAP"][1] += f["out_tokens"] or 0
                        tot["THINK"][0] += inp[think][i]; tot["THINK"][1] += t["out_tokens"] or 0
                        tot["FF"][0] += inp[c][i] + (inp[think][i] if esc else 0); tot["FF"][1] += (f["out_tokens"] or 0) + ((t["out_tokens"] or 0) if esc else 0)
                if not cnt:
                    continue
                th = sum(tot["THINK"])
                print(f"  {m:5s} cheap={c:5s} " + " | ".join(f"{k} in {a / cnt / 1000:.2f}k out {b / cnt / 1000:.2f}k" for k, (a, b) in tot.items())
                      + f" | FF / THINK: output {100 * tot['FF'][1] / max(1, tot['THINK'][1]):.0f}%, input + output {100 * sum(tot['FF']) / max(1, th):.0f}%")


if __name__ == "__main__":
    main()
