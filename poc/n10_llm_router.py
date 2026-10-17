"""N10 stage 2 (PREREG_N10.md, P4): the LLM router. For every item whose first attempt fails the label-free check, the model
(Qwen3-32B-AWQ, no thinking, T = 0) sees the task, its program and the check feedback, and picks one fix from the menu; the item's
outcome is then read from the N10 factorial (same instances). Tokens = first attempt + router call + the chosen fix.
usage: POC_BASE_URL=... python n10_llm_router.py   -> results/n10_llm_router.json and a printed comparison"""
import json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as A  # noqa: E402
from llm import chat  # noqa: E402
from run_co import describe, gen  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402

MENU = {"geo": {"A": ("sample", "write two more programs independently and keep one that passes the check"),
                "B": ("remove", "write the program again with NO helper functions offered"),
                "C": ("choose", "first pick only the helper functions this task really needs, then write the program with those"),
                "D": ("input", "write the program again with the literal input of this instance shown in the prompt"),
                "E": ("plan", "first state the algorithm in one or two sentences, then write the program"),
                "F": ("think", "think step by step at length before writing the program")},
        "co": {"A": ("sample", "write two more programs independently and keep one whose solution is feasible"),
               "B": ("remove", "write the program again with NO documentation"),
               "C": ("choose", "write the program again with the 3 most relevant documentation snippets retrieved for this problem"),
               "D": ("input", "write the program again with the literal input of this instance shown in the prompt"),
               "E": ("plan", "show the program and its error to the model and ask it to fix the program once"),
               "F": ("think", "think step by step at length before writing the program")}}


def feedback(sig, err):
    if sig == "check_fail":
        return {"geo": "Run on shifted, rotated, mirrored and relabelled copies of the input, the program's answers are inconsistent, "
                       "so it is wrong on at least some of them.", "co": "The program's printed solution is INFEASIBLE."}
    if sig == "no_code":
        return "No program was found in the answer."
    if sig == "timeout":
        return "The program ran out of time."
    if sig == "no_output":
        return "The program printed nothing."
    return "The program crashed:\n" + (err or sig)[-800:]


def main():
    out = {}
    for dom in ("geo", "co"):
        rows, keys = A.load(dom)
        O, SIG, TASK = A.outcomes(dom, rows, keys)
        fail = [k for k in keys if not O[k]["first"][2]]
        acc = tok = 0; picks = {}
        for k in keys:
            o = O[k]; c, t = o["first"][0], o["first"][1]
            if k in fail:
                r = rows["first"][k]
                if dom == "geo":
                    rng = random.Random(f"{k[0]}-{k[1]}-{k[2]}")
                    task_txt = render(k[0], variants(k[0], base_instance(k[0], k[1], rng), rng)["identity"])[0]
                    err = ""
                else:
                    task_txt = describe(r["prob"], gen(r["prob"], r["n"], random.Random(k)))[0]
                    err = r.get("err") or ""
                menu = "\n".join(f"{L}: {d}" for L, (_, d) in MENU[dom].items())
                fb = feedback(SIG[k], err)
                fb = fb[dom] if isinstance(fb, dict) else fb
                q = (f"A model was asked to write a Python program for this task:\n{task_txt}\n\nIts program:\n```python\n{(r.get('code') or '')[:6000]}\n```\n\n"
                     f"What happened: {fb}\n\n"
                     f"Which ONE of these fixes is most likely to give a correct program?\n{menu}\n\nAnswer with one line: `FIX: <letter>`.")
                rr = chat(q, think=False, max_tokens=256, temperature=0.0, seed=1)
                m = re.findall(r"FIX:\s*\**\s*([A-F])", rr["text"] or "")
                L = m[-1] if m else "F"
                f = MENU[dom][L][0]; picks[str(k)] = f
                c, t = o[f][0], t + (rr.get("out_tokens") or 0) + o[f][1]
            acc += c; tok += t
        out[dom] = {"acc": 100 * acc / len(keys), "tok": tok / len(keys), "picks": picks}
        from collections import Counter
        print(f"{dom}: LLM router {100 * acc / len(keys):.1f}% @ {tok / len(keys):.0f} tokens per item; picks {dict(Counter(picks.values()))}", flush=True)
    json.dump(out, open(f"{A.RES}/n10_llm_router.json", "w"))


if __name__ == "__main__":
    main()
