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


def grade(z):
    sat, sol = read(z.get("final")); v = check(z["id"], sat, sol); out = {"id": z["id"], "correct": bool(v["correct"]), "claim": sat, "details": str(v["details"])[:200]}
    if sat is None:          # lenient reading: the raw message (TIR2) or the stored final
        s2, so2 = read_lenient(z.get("raw") or z.get("final")); v2 = check(z["id"], s2, so2)
        out.update(correct_len=bool(v2["correct"]), claim_len=s2)
    else:
        out.update(correct_len=out["correct"], claim_len=sat)
    return out


def ref(p):
    from math_constraint.eval import validate_answer
    v = validate_answer(p, True, p["solution"])
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
    for path in sys.argv[1:]:
        Z = [json.loads(l) for l in open(path)]; out = path.replace(".jsonl", ".graded.jsonl")
        with ProcessPoolExecutor(W) as ex:
            G = list(ex.map(grade, Z))
        with open(out, "w") as f:
            for g in G:
                f.write(json.dumps(g) + "\n")
        print(f"{os.path.basename(path)}: {sum(g['correct'] for g in G)} of {len(G)} correct", flush=True)
