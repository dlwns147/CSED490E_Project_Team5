"""MCST grader (PREREG_DIFF, 2026-11-28): the benchmark's own validate_answer (2605.08498 repo, commit 687a6d5; pycsp3 + Java / pysat) on
the answers written by poc/mcst_run.py. A box / submission is read as UNSATISFIABLE (sat = False) or as a JSON (else Python-literal) list
(sat = True); anything else is unparsed (wrong). Output: <rows>.graded.jsonl with id, correct, claim, details. `ref` verifies the dataset's own
reference solutions (a check of the verifier). Run with the verifier venv: PATH=<jre>/bin:$PATH /root/venvs/mcst/bin/python mcst_grade.py <rows.jsonl> ...
Temporary files: validate_answer writes its model files in a TemporaryDirectory that it removes itself."""
import ast, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor
DATA = os.environ.get("MCST_DATA", "/dev/shm/sj_nlp/mcst/Math-Constraint/mathconstraint/problems.jsonl")
P = {p["name"]: p for p in map(json.loads, open(DATA))}


def read(s):
    s = (s or "").strip()
    if re.search(r"(?i)\bunsat", s):
        return False, None
    for f in (json.loads, ast.literal_eval):
        try:
            v = f(s)
            if isinstance(v, (list, dict)):
                return True, v
        except Exception:
            pass
    return None, None


def read_lenient(t):
    """amendment 2026-11-28 12:32 UTC: the last bracketed list in the message that parses, else the word UNSATISFIABLE; same for every arm"""
    t = t or ""; ends = [i for i, ch in enumerate(t) if ch == "]"]
    for e in reversed(ends):
        depth = 0
        for i in range(e, -1, -1):
            depth += (t[i] == "]") - (t[i] == "[")
            if depth == 0:
                sat, sol = read(t[i:e + 1])
                if sat:
                    return sat, sol
                break
    return (False, None) if re.search(r"(?i)\bunsat", t) else (None, None)


def check(k, sat, sol):
    from math_constraint.eval import validate_answer
    if sat is None:
        return {"correct": False, "details": "unparsed"}
    try:
        return validate_answer(P[k], sat, sol)
    except Exception as e:
        return {"correct": False, "details": f"grader error {type(e).__name__}: {str(e)[:100]}"}


# FIX (2026-11-28 12:47 UTC): three verifier models contain symmetry-breaking constraints that their prompts do not state, so valid answers are
# rejected (found on a graph colouring answer with 0 conflicting edges, graded "violates constraints"). correct_fix = the same verifier with only
# these lines removed (symmetry breaking does not change satisfiability, so the SAT / UNSAT labels stand). Prompts that state their convention
# (golomb, knight_tour, non_transitive_dice, sidon_set) are untouched.
UNSTATED = {"graph_k_coloring": "    # symmetry break\n    x[0] == 0,\n",
            "number_partitioning": "    # symmetry breaking: 1 always in subset 0\n    x[0] == 0,\n",
            "social_golfers": "    # symmetry breaking: week 0 has players 0..gs-1 in group 0, gs..2gs-1 in group 1, ...\n    [assign(0, p) == p // group_size for p in range(n_players)],\n"}


# FIX, part 2 (2026-11-28 13:05 UTC): low_autocorrelation's verifier uses bound max(4, round(0.1 n^2)) ("tightened from n^1.3", problems.py),
# while the prompts state the old bound (n^1.3: 20 at n = 10, where the verifier uses 10); for n <= 26 valid answers under the stated bound are
# rejected (all 9 rejected reference solutions are of this kind). correct_fix verifies against the bound the prompt states.


def check_fix(k, sat, sol):
    from math_constraint import csp_solver as CS
    t = P[k]["problem_type"]
    if t not in UNSTATED and t != "low_autocorrelation" or sat is not True:
        return check(k, sat, sol)
    orig = CS._MODELS[t]["model"]
    def stripped(**kw):
        code = orig(**kw)
        if t == "low_autocorrelation":
            b = re.search(r"must be at most (\d+)", P[k]["prompt"]).group(1); assert re.search(r"(?m)^bound = \d+$", code)
            return re.sub(r"(?m)^bound = \d+$", "bound = " + b, code)
        assert UNSTATED[t] in code, t; return code.replace(UNSTATED[t], "")
    CS._MODELS[t]["model"] = stripped
    try:
        return check(k, sat, sol)
    finally:
        CS._MODELS[t]["model"] = orig


def grade(z):
    sat, sol = read(z.get("final")); v = check(z["id"], sat, sol); out = {"id": z["id"], "correct": bool(v["correct"]), "claim": sat, "details": str(v["details"])[:200]}
    out["correct_fix"] = bool(check_fix(z["id"], sat, sol)["correct"]) if not out["correct"] else True
    if sat is None:          # lenient reading: the raw message (TIR2) or the stored final
        s2, so2 = read_lenient(z.get("raw") or z.get("final")); v2 = check(z["id"], s2, so2)
        out.update(correct_len=bool(v2["correct"]), claim_len=s2, correct_len_fix=bool(v2["correct"]) or bool(check_fix(z["id"], s2, so2)["correct"]))
    else:
        out.update(correct_len=out["correct"], claim_len=sat, correct_len_fix=out["correct_fix"])
    return out


def ref(p):
    v = check_fix(p["name"], True, p["solution"]) if os.environ.get("REF_FIX") else check(p["name"], True, p["solution"])
    return p["name"], p["problem_type"], bool(v["correct"]), str(v["details"])[:160]


if __name__ == "__main__":
    W = int(os.environ.get("GRADE_PROCS", 12))
    if sys.argv[1] == "ref":
        with ProcessPoolExecutor(W) as ex:
            out = list(ex.map(ref, [p for p in P.values() if p["satisfiable"]]))
        bad = [o for o in out if not o[2]]; ty = sorted({o[1] for o in bad})
        print(f"reference solutions verified {len(out) - len(bad)} of {len(out)}; failing types {ty}", flush=True)
        for o in bad[:5]:
            print(" ", o)
        json.dump([o[0] for o in bad], open(os.environ.get("REF_OUT", "/dev/shm/sj_nlp/mcst/ref_fail.json"), "w"))
        sys.exit()
    if sys.argv[1] == "paper":      # the authors' harness output (their tools.json): official and fixed grade of their submissions
        for path in sys.argv[2:]:
            R = json.load(open(path))["results"]; Z = []
            for r in R:
                st = r.get("submitted_satisfiable"); sol = r.get("submitted_solution")
                fin = "UNSATISFIABLE" if str(st) == "False" else (json.dumps(ast.literal_eval(sol)) if isinstance(sol, str) and sol not in ("None", "") else (json.dumps(sol) if sol is not None else ""))
                Z.append({"id": r["problem_name"], "final": fin if str(st) in ("True", "False") else ""})
            with ProcessPoolExecutor(W) as ex:
                G = list(ex.map(grade, Z))
            off = {r["problem_name"]: str(r["correct"]) == "True" for r in R}
            print(f"{path}: their grade {sum(off.values())}, regraded official {sum(g['correct'] for g in G)}, fixed {sum(g['correct_fix'] for g in G)} of {len(G)}", flush=True)
            json.dump({g["id"]: g for g in G}, open(path.replace(".json", ".regraded.json"), "w"))
        sys.exit()
    for path in sys.argv[1:]:
        Z = [json.loads(l) for l in open(path)]; out = path.replace(".jsonl", ".graded.jsonl")
        with ProcessPoolExecutor(W) as ex:
            G = list(ex.map(grade, Z))
        with open(out, "w") as f:
            for g in G:
                f.write(json.dumps(g) + "\n")
        print(f"{os.path.basename(path)}: {sum(g['correct'] for g in G)} of {len(G)} correct; with the unstated symmetry lines removed {sum(g['correct_fix'] for g in G)}", flush=True)
