"""G2-deep — metamorphic SELF-REPAIR of LLM-written geometry code (label-free).

1. The model writes a program from the identity prompt (as in G2b).
2. Label-free check: run it on transformed copies of the SAME given instance (translate, rot90, mirror, permute,
   scale x3, ~1e9 offset). Their answers must agree (area2/close scale x9), so disagreement or a crash reveals a
   bug WITHOUT any ground truth.
3. If the check fails, feed back up to 3 disagreeing pairs (both inputs + outputs + the relation) and ask for a fix;
   up to R rounds.
Conditions: none (R=0), mr (label-free feedback), oracle (feedback with the TRUE answers for failing variants: an
upper bound). Final evaluation with the exact oracle: all 8 variants of the base instance, plus 5 FRESH instances
(with their 8 variants each) to test that the repaired program generalises.
Also stored: the code and a float-usage flag (float()/true division/atan2/sqrt/hypot/math.pi) for the mechanism
analysis.
"""
import argparse
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
SIZES = {"hull": (10, 20), "area2": (8, 14), "pip": (8, 14), "segs": (6, 10), "close": (10, 20)}
MR = ["translate", "rot90", "mirror", "permute", "scale", "big"]
REL = {"translate": "the same geometry shifted by a constant vector", "rot90": "the same geometry rotated by 90 degrees",
       "mirror": "the same geometry mirrored (x -> -x)", "permute": "the same geometry with the input order shuffled "
       "(for a polygon: a different starting vertex and/or reversed orientation)",
       "scale": "the same geometry scaled by 3", "big": "the same geometry shifted by about 10^9"}
FLOAT_RE = re.compile(r"float\(|math\.(atan2|sqrt|hypot|pi|cos|sin)|(?<![/])/(?![/=])|1e-|eps")


def run_out(code, task, x):
    _, stdin, _ = render(task, x)
    r = run_python(code, stdin, timeout=10)
    return (r.stdout.strip().split() or [None])[-1].lower() if r.status == "ok" and r.stdout.strip() else None


def expected_rel(task, v, base_out):
    if base_out is None:
        return None
    if v == "scale" and task == "clip":
        from fractions import Fraction
        try:
            x = Fraction(base_out) * 9
            return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
        except (ValueError, ZeroDivisionError):
            return None
    if v == "scale" and task in ("area2", "close", "rectunion", "diameter", "closeL", "diamL"):
        try:
            return str(int(base_out) * 9)
        except ValueError:
            return None
    return base_out


def mr_check(code, task, V):
    base = run_out(code, task, V["identity"])
    bad = []
    for v in MR:
        if task == "lattice" and v == "scale":   # Pick count has no closed-form relation under scaling
            continue
        o = run_out(code, task, V[v])
        if base is None or o is None or o != expected_rel(task, v, base):
            bad.append((v, o))
    return base, bad


def evaluate(code, task, n, seed_key):
    """exact-oracle accuracy over the 8 variants of the base instance + 5 fresh instances"""
    res = []
    for k, key in enumerate([seed_key] + [f"{seed_key}-fresh{j}" for j in range(5)]):
        rng = random.Random(key)
        V = variants(task, base_instance(task, n, rng), rng)
        for vn, x in V.items():
            res.append({"fresh": k > 0, "variant": vn, "ok": run_out(code, task, x) == answer(task, x)})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--n_inst", type=int, default=10)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--conds", default="none,mr,oracle")
    a = ap.parse_args()
    jobs = [(task, n, i, c) for task, ns in SIZES.items() for n in ns for i in range(a.n_inst) for c in a.conds.split(",")]

    def run(j):
        task, n, i, cond = j
        key = f"{task}-{n}-{i}"
        rng = random.Random(key)
        V = variants(task, base_instance(task, n, rng), rng)
        q, _, fmt = render(task, V["identity"])
        msgs = [{"role": "user", "content": f"{q}\n\nDo not compute the answer by hand. Write a Python 3 program that "
                 f"solves this problem for any input in the following stdin format: {fmt}. Print only the answer. "
                 f"Give the program in a single ```python code block."}]
        o = chat_msgs(msgs, max_tokens=a.max_tokens, temperature=0.0)
        code = last_block(o["text"], ("python", "py", "python3")) or ""
        hist = [{"round": 0, "float": bool(FLOAT_RE.search(code))}]
        rounds_used = 0
        for rnd in range(1, (a.rounds if cond != "none" else 0) + 1):
            base, bad = mr_check(code, task, V)
            if cond == "oracle":
                bad = [(v, run_out(code, task, V[v])) for v in ["identity"] + MR if run_out(code, task, V[v]) != answer(task, V[v])]
            if not bad:
                break
            parts = []
            for v, out in bad[:3]:
                _, stdin_v, _ = render(task, V[v])
                if cond == "oracle":
                    parts.append(f"Input:\n{stdin_v}\nYour program printed: {out}. The correct answer is: {answer(task, V[v])}.")
                else:
                    _, stdin_i, _ = render(task, V["identity"])
                    want = expected_rel(task, v, base)
                    parts.append(f"Input A:\n{stdin_i}\nYour program printed: {base}.\nInput B ({REL[v]}):\n{stdin_v}\n"
                                 f"Your program printed: {out}, but since B is {REL[v]}, the answer must be "
                                 f"{'9 times' if v == 'scale' and task in ('area2', 'close') else 'the same as'} for A"
                                 f"{f' (= {want})' if want else ''}. At least one of the two outputs is wrong.")
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": "Your program is inconsistent/incorrect on these tests:\n\n" + "\n\n".join(parts) +
                      "\n\nFind the bug and give the complete corrected program in a single ```python code block."}]
            o = chat_msgs(msgs, max_tokens=a.max_tokens, temperature=0.0)
            code = last_block(o["text"], ("python", "py", "python3")) or code
            rounds_used = rnd
            hist.append({"round": rnd, "float": bool(FLOAT_RE.search(code))})
        ev = evaluate(code, task, n, key)
        return {"task": task, "n": n, "inst": i, "cond": cond, "rounds": rounds_used, "hist": hist,
                "acc_base": sum(e["ok"] for e in ev if not e["fresh"]) / 8,
                "acc_fresh": sum(e["ok"] for e in ev if e["fresh"]) / max(1, sum(e["fresh"] for e in ev)),
                "all_ok_base": all(e["ok"] for e in ev if not e["fresh"]),
                "all_ok_fresh": all(e["ok"] for e in ev if e["fresh"]), "code": code}
    with ThreadPoolExecutor(48) as ex, open(f"{RES}/geomr_{a.model_tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
    import numpy as np
    rows = [json.loads(l) for l in open(f"{RES}/geomr_{a.model_tag}.jsonl")]
    for c in a.conds.split(","):
        rs = [r for r in rows if r["cond"] == c]
        print(f"{a.model_tag} {c:7s} all-variants-correct base {np.mean([r['all_ok_base'] for r in rs]):.2f}  "
              f"fresh-instances all-correct {np.mean([r['all_ok_fresh'] for r in rs]):.2f}  "
              f"acc_fresh {np.mean([r['acc_fresh'] for r in rs]):.3f}  mean rounds {np.mean([r['rounds'] for r in rs]):.2f}")
        for t in SIZES:
            tr = [r for r in rs if r["task"] == t]
            print(f"    {t:6s} base {np.mean([r['all_ok_base'] for r in tr]):.2f}  fresh {np.mean([r['all_ok_fresh'] for r in tr]):.2f}")


if __name__ == "__main__":
    main()
