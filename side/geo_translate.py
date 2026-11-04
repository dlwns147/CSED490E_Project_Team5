"""SIDE-GT (docs/prereg/PREREG_SIDE.md): exact geometry proofs from a small model. The model only translates a competition geometry
statement into AlphaGeometry's construction language, as Newclid 2 reads it (Sicca et al., 2411.11938; pip `newclid>=2,<3`); the
problem's own conclusion guards the translation; Newclid's DDAR (deduction + algebraic reasoning, CPU only) proves it.
  gen    the model writes k translations per problem -> results/proof/gt_<tag>.jsonl (id, sample, dsl, tokens)
  check  per translation: parse; build the premises alone on 8 random diagrams; the guard passes when the goal holds numerically
         (to 1e-7) on at least one (a false goal holds on none); a guarded translation then goes to DDAR with a timeout
         -> results/proof/gt_<tag>_check.jsonl (status: unexpressible / no translation / syntax error / build error / goal fails /
         trivial (the goal already holds among the construction's facts) / guarded; proved true or false; seconds)
A proof DDAR finds is a proof of the translated statement. It is a proof of the problem only when the translation is faithful, which
the guard does not decide: a translation that adds a hypothesis passes it. Faithfulness is read by hand (dev) or compared with a
reference translation (IMO-AG-30's, where one exists).
Problems: $POC_DATA/geo/problems.jsonl (id, source, problem, ref = reference translation or null).
usage: $P side/geo_translate.py gen <tag> <ids file> [--think] [--k K] [--max_tokens N] [--repair R] [--grammar]   (lane.sh job;
       POC_BASE_URL set; --repair needs Newclid on PYTHONPATH: up to R more turns, each told the guard's finding; --grammar: after each
       free reply, one quick greedy turn writes the final line under the language's grammar, vLLM structured outputs)
       <python with newclid> side/geo_translate.py check <tag> [--timeout S] [--workers W]     (CPU job)"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "poc"))
PD = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "geo")
OUT = os.path.join(ROOT, "results", "proof")

LEGEND = """Predicates (points are lowercase names such as a, b, o1, h_a):
  coll a b c: a, b, c are collinear.            para a b c d: line ab is parallel to line cd.
  perp a b c d: line ab is perpendicular to cd.  cong a b c d: segment ab has the same length as cd.
  cyclic a b c d: a, b, c, d lie on one circle.  midp m a b: m is the midpoint of ab.
  eqangle a b c d e f g h: the angle from line ab to line cd equals the angle from line ef to line gh (directed, modulo 180 degrees).
  eqratio a b c d e f g h: ab / cd = ef / gh.
  simtri a b c x y z: triangles abc and xyz are similar.   contri a b c x y z: they are congruent.
  aconst a b c d 2pi/3: the angle from line ab to line cd is the given constant (a fraction of pi)."""

RULES = """Rules:
- A translation is one line: construction steps separated by "; ", then " ? ", then exactly one goal predicate.
- Each step defines new points from points defined earlier: `x = construction x args` or, for an intersection of two loci,
  `x = construction1 x args, construction2 x args`. The first step creates the free points, e.g. `a b c = triangle a b c`.
- A point defined by a line and a circle (or two circles) that already pass through a known point is the other intersection.
- Use only the constructions listed. Name points as the problem does, in lowercase.
- If the statement has several parts, translate the first claim to prove. For "if and only if", put the hypothesis of one direction
  into the construction and the other side in the goal.
- If the statement cannot be written with these constructions and predicates (inequalities, numerical lengths, existence of a
  configuration, counting), reply `UNEXPRESSIBLE` instead.
Reply with the translation only, in one ``` code block."""

EXAMPLES = [   # checked with Newclid 2.0.2 (11-04): each passes the guard; DDAR proves all but the first, which needs an extra point
    ("Let ABC be a triangle. The altitudes from B and C meet at H. Prove that AH is perpendicular to BC.",
     "a b c = triangle a b c; h = on_tline h b a c, on_tline h c a b ? perp a h b c"),
    ("Let ABC be a triangle with circumcircle w. The bisector of angle BAC meets w again at D. Prove that DB = DC.",
     "a b c = triangle a b c; o = circle o a b c; d = angle_bisector d b a c, on_circle d o a ? cong d b d c"),
    ("In triangle ABC, let D be the foot of the altitude from A, and let E, F, M be the midpoints of CA, AB, BC. Prove that D, E, F, "
     "M lie on a circle.",
     "a b c = triangle a b c; d = foot d a b c; e = midpoint e c a; f = midpoint f a b; m = midpoint m b c ? cyclic d e f m"),
    ("The tangent at A to the circumcircle of triangle ABC meets line BC at T. Prove that TA^2 = TB * TC.",
     "a b c = triangle a b c; o = circle o a b c; t = lc_tangent t a o, on_line t b c ? eqratio t a t b t c t a"),
    ("Let I be the incenter of triangle ABC, and let line AI meet the circumcircle of ABC again at M. Prove that MB = MI.",
     "a b c = triangle a b c; i = incenter i a b c; o = circle o a b c; m = on_line m a i, on_circle m o a ? cong m b m i"),
    ("Let M be the midpoint of side BC of triangle ABC, and let D be the reflection of A in M. Prove that AB is parallel to CD.",
     "a b c = triangle a b c; m = midpoint m b c; d = mirror d a m ? para a b c d"),
]


def reference():
    """the construction list, read from Newclid's definitions: name, arguments, and what the new point satisfies"""
    out = []
    for block in open(os.path.join(PD, "newclid_defs.txt")).read().strip().split("\n\n"):
        L = [l.strip() for l in block.strip().splitlines()]
        if len(L) < 4 or L[3].startswith("="):
            out.append(f"  {L[0]}" + (f"   (free points{': ' + L[3][1:].strip() if len(L) > 3 and L[3][1:].strip() else ''})"
                                     if len(L) > 1 else ""))
            continue
        req = L[2].split("=", 1)[1].strip() if "=" in L[2] else ""
        out.append(f"  {L[0]}: {L[3].split(':', 1)[1].strip()}" + (f"   (requires {req})" if req else ""))
    return "Constructions (name and arguments: what the new point satisfies):\n" + "\n".join(out)


def prompt(problem):
    ex = "\n\n".join(f"Problem: {p}\nTranslation:\n```\n{t}\n```" for p, t in EXAMPLES)
    return (f"Translate the following olympiad geometry problem into AlphaGeometry's construction language. Do not prove it.\n\n"
            f"{reference()}\n\n{LEGEND}\n\n{RULES}\n\nExamples:\n\n{ex}\n\nProblem: {problem}\nTranslation:")


def dsl_of(text):
    b = re.findall(r"```[a-zA-Z0-9]*[ \t]*\r?\n(.*?)```", text, flags=re.S)
    t = (b[-1] if b else text).strip()
    if "UNEXPRESSIBLE" in t:
        return "UNEXPRESSIBLE"
    lines = [l.strip() for l in t.splitlines() if " ? " in l]
    return lines[-1] if lines else None


def grammar():
    """EBNF (vLLM structured_outputs grammar, xgrammar) of a reply: one code block holding UNEXPRESSIBLE or steps of the listed constructions, each
    with its own number of arguments (typed ones as constants: Angle 2pi/3 or 60o, Ratio 1/2, Length 3), ' ? ' and one goal predicate
    with its number of points. It removes the unknown constructions and wrong argument counts; it does not check meaning."""
    kind = {"Angle": "ang", "Ratio": "rat", "Length": "len"}
    con = []
    for block in open(os.path.join(PD, "newclid_defs.txt")).read().strip().split("\n\n"):
        h = block.strip().splitlines()[0].split()
        if h and h[0] != "=":
            con.append(f'"{h[0]}"' + "".join(f' " " {kind[a.split(":")[1]] if ":" in a else "nm"}' for a in h[1:]))
    goal = [f'"{p}"' + ' " " nm' * n for p, n in (("coll", 3), ("para", 4), ("perp", 4), ("cong", 4), ("cyclic", 4), ("midp", 3),
                                                    ("eqangle", 8), ("eqratio", 8), ("simtri", 6), ("contri", 6))]
    goal.append('"aconst"' + ' " " nm' * 4 + ' " " ang')
    return "\n".join(['root ::= "```\\n" body "\\n```"', 'body ::= "UNEXPRESSIBLE" | step ("; " step)* " ? " goal',
                      'step ::= nm (" " nm)* " = " con (", " con)*', "con ::= " + " | ".join(con), "goal ::= " + " | ".join(goal),
                      "nm ::= [a-z] [a-z0-9_]*", 'ang ::= [0-9]+ "pi/" [0-9]+ | [0-9]+ "o"', 'rat ::= [0-9]+ "/" [0-9]+',
                      'len ::= [0-9]+ ("." [0-9]+)?'])


FINAL = """Now write the final translation in the required form: steps that use only the listed constructions, each with exactly its listed
arguments, then " ? " and one goal predicate (or UNEXPRESSIBLE), in one ``` code block."""

REPAIR = """Newclid cannot use this translation. {what}
Write a corrected translation of the same problem, following the same rules. Reply with the translation only, in one ``` code block."""


def guard(dsl):
    """the checker's verdict without DDAR, in a subprocess (needs Newclid on PYTHONPATH): (status, message)"""
    if dsl in (None, "UNEXPRESSIBLE"):
        return ("no translation" if dsl is None else "unexpressible"), ""
    try:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "one", dsl, "0"], capture_output=True, text=True, timeout=900)
        st, _, msg, _ = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as e:
        st, msg = "build error", f"checker: {type(e).__name__}"
    return st, msg


def gen():
    from llm import chat_msgs
    tag, ids_file = sys.argv[2], sys.argv[3]
    think = "--think" in sys.argv
    k = int(sys.argv[sys.argv.index("--k") + 1]) if "--k" in sys.argv else 8
    rep = int(sys.argv[sys.argv.index("--repair") + 1]) if "--repair" in sys.argv else 0
    gram = grammar() if "--grammar" in sys.argv else None
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else (16000 if think else 2048)
    want = set(open(ids_file).read().split())
    X = [x for x in map(json.loads, open(os.path.join(PD, "problems.jsonl"))) if x["id"] in want]
    os.makedirs(OUT, exist_ok=True)
    out = f"{OUT}/gt_{tag}.jsonl"
    done = {(r["id"], r["sample"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [(x, s) for x in X for s in range(k) if (x["id"], s) not in done]
    print(f"SIDE-GT gen {tag}: {len(todo)} translations of {len(X)} problems (think={think}, k={k}, repair={rep}, grammar={bool(gram)})",
          flush=True)

    def one(x, s):
        msgs, rounds = [{"role": "user", "content": prompt(x["problem"])}], []
        for i in range(rep + 1):   # --repair R: up to R more turns, each told what the guard found (the main recipe's repair turn)
            r = chat_msgs(msgs, think=think, max_tokens=mt, temperature=0.6 if think else 0.7)
            draft = dsl_of(r["text"])
            if gram:   # --grammar: the free reply, then its final line rewritten under the grammar (quick, greedy)
                q = chat_msgs(msgs + [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": FINAL}], think=False,
                              max_tokens=1024, temperature=0, extra={"structured_outputs": {"grammar": gram}})   # vLLM 0.22
                r = dict(r, text=q["text"], out_tokens=r["out_tokens"] + q["out_tokens"], in_tokens=r["in_tokens"] + q["in_tokens"])
            d = dsl_of(r["text"])
            st, msg = guard(d) if rep else ("", "")
            rounds.append({"dsl": d, "status": st, "msg": msg[:300], "out_tokens": r["out_tokens"], "in_tokens": r["in_tokens"],
                           **({"draft": draft} if gram else {})})
            if not rep or st in ("guarded", "unexpressible") or i == rep:
                break
            what = {"goal fails": "The goal does not hold on any figure built from your constructions, so the constructions or the goal "
                                  "do not match the problem.",
                    "copied example": "It repeats one of the examples instead of translating this problem.",
                    "trivial": "The goal already follows from the constructions themselves, before any reasoning, so it is not the "
                               "problem's claim.",
                    "no translation": "No line with ' ? ' and a goal was found in your reply."}.get(st, f"{st}: {msg}")
            msgs += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": REPAIR.format(what=what)}]
        return {"id": x["id"], "sample": s, "dsl": d, "out_tokens": sum(q["out_tokens"] for q in rounds),
                "in_tokens": sum(q["in_tokens"] for q in rounds), "finish": r["finish"], "text": r["text"][-1500:], "rounds": rounds}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for fu in as_completed([ex.submit(one, x, s) for x, s in todo]):
            try:
                r = fu.result()
            except Exception as e:
                print(f"  failed: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
            f.write(json.dumps(r) + "\n"); f.flush()


def one_check(dsl, timeout):
    """(status, proved, seconds) for one translation; runs inside its own process (Newclid's diagram search can loop)"""
    import time
    import numpy as np
    from newclid import GeometricSolverBuilder
    from newclid.defs.clause import Construction
    from newclid.numerical.check import check_numerical
    from newclid.problem import Problem
    from newclid.statements.statement import Statement
    t0 = time.time()
    if dsl.split(" ? ")[0].strip() in {e[1].split(" ? ")[0] for e in EXAMPLES}:   # dev 11-04: all 3 guarded Qwen3-8B translations
        return "copied example", None, "", 0.0                                     # were example 3, copied (a true theorem)
    try:
        goal = Construction.from_txt(dsl.split(" ? ")[1].strip())
        Problem.from_txt(dsl, translate=False)
    except Exception as e:
        return "syntax error", None, f"{type(e).__name__}: {str(e)[:200]}", 0.0
    import newclid.numerical.check as nc   # Newclid compares with an absolute 1e-12, which true goals miss by rounding (dev, 11-04)
    nc.ATOM, nc.close_enough = 1e-7, (lambda a, b, tol=1e-7: abs(a - b) < tol)
    held = 0
    for seed in range(8):   # the guard: premises alone, 8 independent diagrams
        try:
            s = GeometricSolverBuilder(seed=seed, no_goal=True).load_problem_from_txt(dsl, translate=False).build()
        except Exception as e:
            return "build error", None, f"{type(e).__name__}: {str(e)[:200]}", time.time() - t0
        try:
            held += bool(check_numerical(Statement(goal.name, s.proof_state.map_construction_args_to_objects(goal))))
        except Exception as e:
            return "syntax error", None, f"goal: {type(e).__name__}: {str(e)[:200]}", time.time() - t0
    # A construction step with two intersection points takes either at random, and a problem's claim usually holds for one of them
    # (IMO 2017 P4: "the common point closest to R"; IMO-AG-30's own translations fail an all-8 rule 4 times in 30). A false goal
    # holds on no random diagram, so the guard asks for at least one; `held` reports how many.
    if not held:
        return "goal fails", None, "held on 0 of 8 diagrams", time.time() - t0
    # The second test (dev 3, 11-04: every translation the grammar run passed was true by construction, a ratio equal to itself or
    # three points built on one line): a competition conclusion is never already one of the hypotheses, so a goal that holds among
    # the construction's facts before any deduction is "trivial". In `check`, and in gen's guard with GT_TRIVIAL=1 (the gen jobs
    # started before it keep their guard).
    trivial_test = timeout > 0 or os.environ.get("GT_TRIVIAL") == "1"
    if timeout <= 0 and not trivial_test:   # the guard alone (gen --repair)
        return "guarded", None, f"held on {held} of 8", time.time() - t0
    try:
        s = GeometricSolverBuilder(seed=0).load_problem_from_txt(dsl, translate=False).build()
        if s.proof_state.check_goals():
            return "trivial", None, "the goal already holds among the construction's facts, before any deduction", time.time() - t0
        if timeout <= 0:
            return "guarded", None, f"held on {held} of 8", time.time() - t0
        proved = bool(s.run(timeout=timeout))
    except Exception as e:
        return "guarded", (None if timeout <= 0 else False), f"held on {held} of 8; DDAR: {type(e).__name__}: {str(e)[:200]}", time.time() - t0
    return "guarded", proved, f"held on {held} of 8", time.time() - t0


def check():
    tag = sys.argv[2]
    timeout = float(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 300.0
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    R = [json.loads(l) for l in open(f"{OUT}/gt_{tag}.jsonl")]
    for r in R:   # re-extract from the stored reply (the extractor may be newer than the rows)
        if r.get("text"):
            r["dsl"] = dsl_of(r["text"])

    def run(r):
        base = {"id": r["id"], "sample": r["sample"], "dsl": r["dsl"]}
        if r["dsl"] in (None, "UNEXPRESSIBLE"):
            return {**base, "status": "no translation" if r["dsl"] is None else "unexpressible", "proved": None, "msg": "", "sec": 0}
        try:
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "one", r["dsl"], str(timeout)], capture_output=True,
                               text=True, timeout=timeout + 600)
            if not p.stdout.strip():
                raise RuntimeError((p.stderr.strip().splitlines() or ["no output"])[-1][:300])
            st, pr, msg, sec = json.loads(p.stdout.strip().splitlines()[-1])
        except subprocess.TimeoutExpired:
            st, pr, msg, sec = "build error", None, "diagram search timed out", timeout + 600
        except Exception as e:
            st, pr, msg, sec = "build error", None, f"checker: {type(e).__name__}: {str(e)[:200]}", 0
        return {**base, "status": st, "proved": pr, "msg": msg, "sec": round(sec, 1)}
    with ThreadPoolExecutor(workers) as ex, open(f"{OUT}/gt_{tag}_check.jsonl", "w") as f:
        for fu in as_completed([ex.submit(run, r) for r in R]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(f"SIDE-GT check {tag}: {len(R)} translations -> {OUT}/gt_{tag}_check.jsonl", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "one":
        import logging
        logging.disable(logging.CRITICAL)
        print(json.dumps(one_check(sys.argv[2], float(sys.argv[3]))))
    else:
        {"gen": gen, "check": check}[sys.argv[1]]()
