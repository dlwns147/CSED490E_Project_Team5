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
       <python with newclid> side/geo_translate.py check <tag> [--timeout S] [--workers W]     (CPU job)
       <python with newclid> side/geo_translate.py aux <tag | refs> [--k K] [--timeout S] [--workers W] [--ids file | --prop <prop tag>]   (CPU job)
       $P side/geo_translate.py propose <tag> <aux file tag> [--think] [--k K] [--m M]   (lane.sh job: the model proposes auxiliary points)"""
import json, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "poc"))
PD = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "geo")
OUT = os.environ.get("GT_OUT", os.path.join(ROOT, "results", "proof"))

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


DECL = bool(os.environ.get("GT_DECL"))   # SIDE-GT-DECL: the statement as points, hypotheses and a goal, with no construction (geo_decl.py)

DECL_LANG = """A statement is one line: `decl:` then the points, then hypotheses, each separated by "; ", then " ? " and exactly one goal.
Hypotheses and goals:
  coll a b c: a, b, c are on one line.   para a b c d: line ab is parallel to line cd.   perp a b c d: line ab is perpendicular to line cd.
  cong a b c d: segments ab and cd have equal length.   midp m a b: m is the midpoint of ab.
  cyclic a b c d: the four points lie on one circle (more points allowed).   circle o a b c: o is the centre of a circle through a, b, c (one or more points after the centre).
  uangle a b c d e f: the angles abc and def (at b and at e, unsigned, as drawn) are equal.
  eqangle a b c d e f g h: the directed angle from line ab to line cd equals that from line ef to line gh, modulo 180 degrees.
  eqratio a b c d e f g h: ab / cd = ef / gh.
Hypotheses only:
  uconst a b c 60: angle abc is 60 degrees.   rconst a b c d 2/3: ab / cd = 2/3.
Order conditions, hypotheses only, which say which configuration is meant:
  between a b c: b is strictly inside segment ac (this also says the three are on one line).   inside p a b c: p is inside triangle abc.
  sameside p q a b: p and q are on the same side of line ab.   opposite p q a b: on opposite sides.   convex a b c d: the quadrilateral is convex, in this order.
  acute a b c: angle abc is acute.   obtuse a b c: it is obtuse.   ncoll a b c: a, b, c are not on one line (write this for every triangle the problem names)."""

DECL_RULES = """Rules:
- Write what the problem states, not how to construct it. Points need no order, and a point may be fixed by conditions that involve later points.
- List every named point, in lowercase. A line gets two named points on it; a circle gets its centre as a new point, or use cyclic. Different names are always different points.
- Write every hypothesis of the problem, and no others. Write the order conditions the problem states (on a side, inside, beyond, convex, acute, between).
- A tangent line at a to a circle with centre o: `perp o a a t` for a point t on the line. Two tangent circles: their centres and the point of tangency are on one line.
- If the statement has several parts, translate the first claim to prove. For "if and only if", put one side in the hypotheses and the other in the goal.
- If the problem or its claim needs sums of lengths, inequalities, areas, a numerical answer, counting, varying n or three dimensions, reply `UNEXPRESSIBLE`.
Reply with the statement only, in one ``` code block."""

DECL_EXAMPLES = [    # each passes the guard of geo_decl.py (written 11-06)
    ("Points E and F lie on sides AB and AC of triangle ABC, with EF parallel to BC and BE = CF. Prove that AB = AC.",
     "decl: a b c e f; ncoll a b c; between a e b; between a f c; para e f b c; cong b e c f ? cong a b a c"),
    ("The incircle of triangle ABC has centre I and touches BC, CA, AB at D, E, F. Prove that angle BID = angle BIF.",
     "decl: a b c i d e f; ncoll a b c; between b d c; between c e a; between a f b; inside i a b c; perp i d b c; perp i e c a; perp i f a b; cong i d i e; cong i e i f ? uangle b i d b i f"),
    ("The tangent at A to the circumcircle of triangle ABC meets line BC at T. Prove that TA^2 = TB * TC.",
     "decl: a b c o t; ncoll a b c; circle o a b c; perp o a a t; coll t b c ? eqratio t a t b t c t a"),
    ("Let P be a point inside triangle ABC with angle PBC = angle PCB and angle PAB = angle PAC. Prove that AB = AC.",
     "decl: a b c p; ncoll a b c; inside p a b c; uangle p b c p c b; uangle p a b p a c ? cong a b a c"),
]


def prompt(problem):
    if DECL:
        ex = "\n\n".join(f"Problem: {p}\nStatement:\n```\n{t}\n```" for p, t in DECL_EXAMPLES)
        return (f"Write the following olympiad geometry problem as a formal statement. Do not prove it.\n\n{DECL_LANG}\n\n{DECL_RULES}\n\nExamples:\n\n{ex}\n\nProblem: {problem}\nStatement:")
    ex = "\n\n".join(f"Problem: {p}\nTranslation:\n```\n{t}\n```" for p, t in EXAMPLES)
    return (f"Translate the following olympiad geometry problem into AlphaGeometry's construction language. Do not prove it.\n\n"
            f"{reference()}\n\n{LEGEND}\n\n{RULES}\n\nExamples:\n\n{ex}\n\nProblem: {problem}\nTranslation:")


def dsl_of(text):
    b = re.findall(r"```[a-zA-Z0-9]*[ \t]*\r?\n(.*?)```", text, flags=re.S)
    t = (b[-1] if b else text).strip()
    if "UNEXPRESSIBLE" in t:
        return "UNEXPRESSIBLE"
    if DECL:
        lines = [l.strip() for l in t.splitlines() if l.strip().startswith("decl:") and " ? " in l]
        return lines[-1] if lines else None
    lines = [l.strip() for l in t.splitlines() if " ? " in l]
    return lines[-1] if lines else None


def grammar():
    """EBNF (vLLM structured_outputs grammar, xgrammar) of a reply: one code block holding UNEXPRESSIBLE or steps of the listed constructions, each
    with its own number of arguments (typed ones as constants: Angle 2pi/3 or 60o, Ratio 1/2, Length 3), ' ? ' and one goal predicate
    with its number of points. It removes the unknown constructions and wrong argument counts; it does not check meaning."""
    if DECL:
        arg = {"coll": 3, "para": 4, "perp": 4, "cong": 4, "midp": 3, "eqangle": 8, "eqratio": 8, "uangle": 6}
        goal = [f'"{p}"' + ' " " nm' * n for p, n in arg.items()] + ['"cyclic" " " nm " " nm " " nm " " nm (" " nm)*', '"circle" " " nm " " nm (" " nm)+']
        hyp = goal + ['"uconst" " " nm " " nm " " nm " " [0-9]+', '"rconst" " " nm " " nm " " nm " " nm " " [0-9]+ "/" [0-9]+'] + \
            [f'"{p}"' + ' " " nm' * n for p, n in (("between", 3), ("inside", 4), ("sameside", 4), ("opposite", 4), ("acute", 3), ("obtuse", 3), ("convex", 4), ("ncoll", 3))]
        return "\n".join(['root ::= "```\\n" body "\\n```"', 'body ::= "UNEXPRESSIBLE" | "decl: " nm (" " nm)* ("; " hyp)* " ? " goal', "hyp ::= " + " | ".join(hyp), "goal ::= " + " | ".join(goal), "nm ::= [a-z] [a-z0-9_]*"])
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
if DECL:
    FINAL = """Now write the final statement in the required form: `decl:`, the points, the hypotheses, then " ? " and one goal (or UNEXPRESSIBLE), in one ``` code block."""

REPAIR = """Newclid cannot use this translation. {what}
Write a corrected translation of the same problem, following the same rules. Reply with the translation only, in one ``` code block."""
if DECL:
    REPAIR = """The checker cannot use this statement. {what}
Write a corrected statement of the same problem, following the same rules. Reply with the statement only, in one ``` code block."""


def guard(dsl):
    """the checker's verdict without DDAR, in a subprocess (needs Newclid on PYTHONPATH): (status, message)"""
    if dsl in (None, "UNEXPRESSIBLE"):
        return ("no translation" if dsl is None else "unexpressible"), ""
    if DECL:
        try:
            p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo_decl.py"), "guard", dsl], capture_output=True, text=True, timeout=900)
            return tuple(json.loads(p.stdout.strip().splitlines()[-1]))
        except Exception as e:
            return "no figure", f"checker: {type(e).__name__}"
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
            what = f"{st}: {msg}" if DECL else {"goal fails": "The goal does not hold on any figure built from your constructions, so the constructions or the goal "
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


def num_holds(st, tol=1e-7):
    """Is a statement true on its figure? Newclid's check of para and perp compares an unnormalized product with 1e-12 whatever tolerance is
    set in numerical.check (LineNum, a module of its own), which fails true statements on rounding alone. Those two are tested here on the
    sine or cosine of the angle between the lines; the rest go through Newclid's check, at the tolerance the caller set there."""
    from newclid.numerical.check import check_numerical
    if st.predicate.value not in ("para", "perp"):
        return bool(check_numerical(st))
    a, b, c, d = (p.num for p in st.args)
    ux, uy, vx, vy = a.x - b.x, a.y - b.y, c.x - d.x, c.y - d.y
    nu, nv = math.hypot(ux, uy), math.hypot(vx, vy)
    if nu == 0 or nv == 0:
        return False
    if st.predicate.value == "perp":
        return bool(abs(ux * vx + uy * vy) / (nu * nv) < tol)
    # same direction: Newclid's `para c p c k` also says that c, p, k are collinear, so two lines that are one are not excluded here
    return bool(abs(ux * vy - uy * vx) / (nu * nv) < tol)


def patch_newclid():
    """GT_CATCH=1 (SIDE-GT-POOL addendum): Newclid 2.0.2 aborts the whole DDAR run when one rule application names a numerically degenerate
    figure, such as a circle through three collinear points. With this, that one application fails and the run goes on; a failed
    application only loses facts."""
    if os.environ.get("GT_SOUND") == "1":
        # SIDE-GT-SOUND: Newclid checks only the goal numerically, and false facts do get in (results/proof/gt_audit.jsonl). A fact is kept, and two
        # symbols are merged, only if it holds on the run's own figure. Rejecting a fact only loses deductions.
        from newclid.agent.agents_interface import ImportDerivationFeedback
        from newclid.proof import Proof, mapping_to_names
        from newclid.statements.adder import StatementAdder
        from newclid.statements.statement import Statement
        orig_t, orig_m = Proof._apply_theorem, StatementAdder._make_equal

        def holds(st):
            try:
                return num_holds(st)
            except Exception:
                return False

        def safe_t(self, theorem, mapping):
            args = self.map_construction_args_to_objects(theorem.conclusion, mapping_to_names(mapping))
            if not holds(Statement(theorem.conclusion.name, tuple(args))):
                return [], [], False
            added, to_cache, ok = orig_t(self, theorem, mapping)
            return [d for d in added if holds(d.statement)], [c for c in to_cache if c is None or holds(c[0])], ok

        def safe_d(self, action):
            if not holds(action.derivation.statement):
                return ImportDerivationFeedback([], [])
            added, to_cache = self.resolve_statement_dependencies(action.derivation.statement, action.derivation.dep_body)
            added, to_cache = [d for d in added if holds(d.statement)], [c for c in to_cache if holds(c[0])]
            self.cache_deps(to_cache)
            return ImportDerivationFeedback(added, to_cache)

        def safe_m(self, x, y, dep):
            if dep is not None and not holds(dep.statement):
                return None
            return orig_m(self, x, y, dep)
        Proof._apply_theorem, Proof._step_apply_derivation, StatementAdder._make_equal = safe_t, safe_d, safe_m
    if os.environ.get("GT_CATCH") != "1":
        return
    from newclid.agent.agents_interface import ApplyTheoremFeedback
    from newclid.numerical.geometries import InvalidLineIntersectError, InvalidQuadSolveError
    from newclid.proof import Proof
    orig = Proof._step_apply_theorem

    def safe(self, action):
        try:
            return orig(self, action)
        except (InvalidLineIntersectError, InvalidQuadSolveError):
            return ApplyTheoremFeedback(False, [], [])
    Proof._step_apply_theorem = safe


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
            held += num_holds(Statement(goal.name, s.proof_state.map_construction_args_to_objects(goal)))
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
    # GT_DDAR_SEEDS (default "0"): diagrams to try in turn when Newclid fails on one (InvalidLineIntersectError and the like depend on
    # the random diagram; dev 4 lost IMO 2012 P5 and IMO 2010 P2 translations to them)
    err = None
    for seed in map(int, os.environ.get("GT_DDAR_SEEDS", "0").split(",")):
        try:
            s = GeometricSolverBuilder(seed=seed).load_problem_from_txt(dsl, translate=False).build()
            if s.proof_state.check_goals():
                return "trivial", None, "the goal already holds among the construction's facts, before any deduction", time.time() - t0
            if timeout <= 0:
                return "guarded", None, f"held on {held} of 8", time.time() - t0
            proved = bool(s.run(timeout=timeout, max_steps=int(os.environ.get("GT_MAX_STEPS", "10000"))))
            return "guarded", proved, f"held on {held} of 8" + (f"; DDAR diagram seed {seed}" if seed else ""), time.time() - t0
        except Exception as e:
            err = e
    return ("guarded", (None if timeout <= 0 else False), f"held on {held} of 8; DDAR: {type(err).__name__}: {str(err)[:200]}",
            time.time() - t0)


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


def aux_candidates(dsl, k, seed=0):
    """k auxiliary points, drawn uniformly (seeded) from one-step classical constructions on the translation's points: midpoints,
    point reflections, circumcentres, feet, line reflections, and intersections of two lines through point pairs. HAGeo (2512.00097)
    reports 25 of IMO-AG-30 for random auxiliary constructions and 28 for its heuristics (code: github.com/boduan1/HAGeo)."""
    import itertools, random
    pts, _ = aux_points(dsl)
    P2, P3 = list(itertools.combinations(pts, 2)), list(itertools.combinations(pts, 3))
    T = {"midpoint": [f"midpoint {{x}} {a} {b}" for a, b in P2],
         "mirror": [f"mirror {{x}} {a} {b}" for a, b in itertools.permutations(pts, 2)],
         "circle": [f"circle {{x}} {a} {b} {c}" for a, b, c in P3],
         "foot": [f"foot {{x}} {a} {b} {c}" for a in pts for b, c in itertools.combinations([q for q in pts if q != a], 2)],
         "reflect": [f"reflect {{x}} {a} {b} {c}" for a in pts for b, c in itertools.combinations([q for q in pts if q != a], 2)],
         "intersection_ll": [f"intersection_ll {{x}} {a} {b} {c} {d}" for (a, b), (c, d) in itertools.combinations(P2, 2)
                             if len({a, b, c, d}) == 4]}
    if os.environ.get("GT_SECOND"):      # second intersections: line and circle through a point, two circles through a point
        T["second_lc"] = [f"second_lc {{x}} {a} {b} {c} {d}" for a in pts for b in pts if b != a for c, d in itertools.combinations([q for q in pts if q != a and q != b], 2)]
        r0 = random.Random(seed + 1)      # too many to list: k drawn uniformly
        T["second_cc"] = list({f"second_cc {{x}} {' '.join(r0.sample(pts, 5))}" for _ in range(k)}) if len(pts) >= 5 else []
    rng = random.Random(seed)
    for v in T.values():
        rng.shuffle(v)
    C = []   # uniform over the construction type, then over its arguments (line intersections would otherwise be ~half the pool)
    while len(C) < k and any(T.values()):
        ty = rng.choice([t for t, v in T.items() if v])
        C.append(T[ty].pop())
    x = next(n for n in ("aux", "aux0", "aux1", "zaux") if n not in pts)
    pre, goal = dsl.split(" ? ")
    return [(c.format(x=x), f"{pre}; {x} = {c.format(x=x)} ? {goal}") for c in C]


PROPOSE = """{problem}

Its translation into AlphaGeometry's construction language:
{dsl}

A deduction engine (DDAR: angle chasing, ratio chasing, similar triangles, cyclic quadrilaterals) could not prove the goal from these
points alone. Olympiad solutions often add an auxiliary point that makes the proof go through: a midpoint, a reflection, a second
intersection of a line and a circle, a circumcentre, the foot of a perpendicular, a parallel through a point. Think about how a solution
of this problem would go, then propose up to {m} different auxiliary points, the most promising first, each built from the points above
with one construction or as the intersection of two.

{ref}"""

PROPOSE_FINAL = """Now write the auxiliary points, one per line, as `{x} = construction {x} args` or `{x} = construction1 {x} args, construction2 {x} args`,
using only the points above, in one ``` code block."""


def aux_points(dsl):
    pts = []
    for step in dsl.split(" ? ")[0].split("; "):
        for q in step.split(" = ")[0].split():
            q = q.split("@")[0]   # IMO-AG-30 fixes some points' coordinates: x@4.96_-0.13
            if q not in pts:
                pts.append(q)
    return pts, next(n for n in ("aux", "aux0", "aux1", "zaux") if n not in pts)


def aux_grammar(dsl):
    """EBNF of a list of auxiliary points for this translation (an input-dependent grammar, Geng et al. 2305.13971): each line defines
    the new point by one or two of Newclid's single-point constructions whose other arguments are existing points (no numeric constants)"""
    pts, x = aux_points(dsl)
    con = []
    for block in open(os.path.join(PD, "newclid_defs.txt")).read().strip().split("\n\n"):
        L = block.strip().splitlines()
        h = L[0].split()
        if not h or h[0] == "=" or len(L) < 2 or ":" not in L[1] or "," in L[1] or any(":" in a for a in h[1:]):
            continue
        new = L[1].split(":")[0].split()
        if len(new) != 1 or len(L[1].split(":")[1].split()) < 2:
            continue
        con.append(f'"{h[0]}"' + "".join(f' " {x}"' if a == new[0] else ' " " P' for a in h[1:]))
    return "\n".join(['root ::= "```\\n" line ("\\n" line)* "\\n```"', f'line ::= "{x} = " con (", " con)?',
                      "con ::= " + " | ".join(con), "P ::= " + " | ".join(f'"{q}"' for q in pts)])


def propose():
    """propose <tag> <aux file tag> [--think] [--k K] [--m M] (lane.sh job): for every row of gt_<aux file tag>_aux.jsonl that DDAR alone
    did not prove, the model reads the statement and the translation and proposes up to M auxiliary points (a free reply, then the list
    under aux_grammar), K samples -> results/proof/gt_<tag>_prop.jsonl (id, sample, dsl, cands, tokens)"""
    from llm import chat_msgs
    tag, src = sys.argv[2], sys.argv[3]
    think = "--think" in sys.argv
    k = int(sys.argv[sys.argv.index("--k") + 1]) if "--k" in sys.argv else 2
    m = int(sys.argv[sys.argv.index("--m") + 1]) if "--m" in sys.argv else 8
    P = {x["id"]: x for x in map(json.loads, open(os.path.join(PD, "problems.jsonl")))}
    AG = {x["ag30"]: x for x in P.values() if x.get("ag30")}   # IMO-AG-30 reference ids -> our problems where we have the statement
    B = [r for r in map(json.loads, open(f"{OUT}/gt_{src}_aux.jsonl")) if r["base"] == "guarded" and not r["base_proved"]]
    out = f"{OUT}/gt_{tag}_prop.jsonl"
    done = {(r["id"], r["sample"], r["s"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [(r, s) for r in B for s in range(k) if (r["id"], r["sample"], s) not in done]
    print(f"SIDE-GT propose {tag}: {len(todo)} proposals for {len(B)} translations (think={think}, k={k}, m={m})", flush=True)

    def one(r, s):
        text = (P.get(r["id"]) or AG.get(r["id"]) or {}).get("problem", "(Only the translation below is available.)")
        _, x = aux_points(r["dsl"])
        msgs = [{"role": "user", "content": PROPOSE.format(problem=text, dsl=r["dsl"], m=m, ref=reference())}]
        a = chat_msgs(msgs, think=think, max_tokens=16000 if think else 2048, temperature=0.6 if think else 0.7)
        q = chat_msgs(msgs + [{"role": "assistant", "content": a["text"]}, {"role": "user", "content": PROPOSE_FINAL.format(x=x)}],
                      think=False, max_tokens=1024, temperature=0, extra={"structured_outputs": {"grammar": aux_grammar(r["dsl"])}})
        body = re.findall(r"```[a-zA-Z0-9]*[ \t]*\r?\n(.*?)```", q["text"], flags=re.S)
        lines = [l.strip() for l in (body[-1] if body else "").splitlines() if l.strip().startswith(f"{x} = ")]
        cands = list(dict.fromkeys(l.split(" = ", 1)[1] for l in lines))[:m]
        return {"id": r["id"], "sample": r["sample"], "s": s, "dsl": r["dsl"], "cands": cands, "out_tokens": a["out_tokens"] + q["out_tokens"],
                "text": a["text"][-1500:]}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for fu in as_completed([ex.submit(one, r, s) for r, s in todo]):
            try:
                f.write(json.dumps(fu.result()) + "\n"); f.flush()
            except Exception as e:
                print(f"  failed: {type(e).__name__}: {str(e)[:200]}", flush=True)


def defs_preds():
    """construction -> (its argument names, the predicates its new points satisfy), from newclid_defs.txt's fourth line of each block"""
    D = {}
    for block in open(os.path.join(PD, "newclid_defs.txt")).read().strip().split("\n\n"):
        L = block.strip().splitlines()
        h = L[0].split()
        if not h or h[0] == "=" or len(L) < 4:
            continue
        pr = [(t.split()[0], t.split()[1:]) for seg in L[3].split(";") if ":" in seg for t in seg.split(":", 1)[1].split(",") if t.split()]
        D[h[0]] = ([a.split(":")[0] for a in h[1:]], pr)
    return D


def preds_of(dsl, D):
    """every predicate the translation's construction steps assert, in its own point names (numeric constants left out)"""
    out = []
    for step in dsl.split(" ? ")[0].split("; "):
        for con in step.split(" = ", 1)[1].split(","):
            t = con.split()
            if not t or t[0] not in D:
                continue
            args, pr = D[t[0]]
            m = dict(zip(args, t[1:]))
            for name, xs in pr:
                if all(x in m for x in xs):
                    out.append((name, [m[x] for x in xs]))
    return out


def one_agree(a, b, seeds=4):
    """does every predicate of translation b (its construction steps and its goal, over points both name) hold on a figure built from
    translation a? Returns
    (holds on some diagram, evaluable / all of b's predicates). Runs inside its own process, as one_check."""
    from newclid import GeometricSolverBuilder
    from newclid.defs.clause import Construction
    from newclid.numerical.check import check_numerical
    from newclid.statements.statement import Statement
    import newclid.numerical.check as nc
    nc.ATOM, nc.close_enough = 1e-7, (lambda u, v, tol=1e-7: abs(u - v) < tol)
    D = defs_preds()
    pa, _ = aux_points(a)
    g = b.split(" ? ")[1].split()
    P = preds_of(b, D) + [(g[0], g[1:])]   # b's goal too: two faithful translations' goals hold on each other's figures
    E = [(n, xs) for n, xs in P if all(x in pa for x in xs)]
    if not E:
        return False, 0.0
    for seed in range(seeds):
        try:
            s = GeometricSolverBuilder(seed=seed, no_goal=True).load_problem_from_txt(a, translate=False).build()
            ok = all(check_numerical(Statement(n, s.proof_state.map_construction_args_to_objects(Construction.from_txt(" ".join([n] + xs)))))
                     for n, xs in E)
        except Exception:
            continue
        if ok:
            return True, len(E) / len(P)
    return False, len(E) / len(P)


def agree():
    """agree <tag> [--workers W]: for every pair of guarded translations of one problem (the last round's status), whether each one's
    construction predicates and goal hold on the other's figure (both directions: the same configuration and claim, up to the names
    they share) -> results/proof/gt_<tag>_agree.jsonl. A label-free check of faithfulness against other samples: an
    added or dropped hypothesis breaks the mutual consistency."""
    import itertools
    tag = sys.argv[2]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    R = [r for r in map(json.loads, open(f"{OUT}/gt_{tag}.jsonl")) if r["rounds"][-1]["status"] == "guarded"]
    by = {}
    for r in R:
        by.setdefault(r["id"], []).append(r)
    jobs = [(i, x, y) for i, rs in by.items() for x, y in itertools.permutations(rs, 2)]

    def run(j):
        i, x, y = j
        try:
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "one_agree", x["dsl"], y["dsl"]], capture_output=True, text=True,
                               timeout=900)
            ok, cov = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            ok, cov = False, 0.0
        return {"id": i, "a": x["sample"], "b": y["sample"], "b_holds_on_a": ok, "coverage": round(cov, 3)}
    with ThreadPoolExecutor(workers) as ex, open(f"{OUT}/gt_{tag}_agree.jsonl", "w") as f:
        for fu in as_completed([ex.submit(run, j) for j in jobs]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(f"SIDE-GT agree {tag}: {len(jobs)} ordered pairs on {len(by)} problems -> {OUT}/gt_{tag}_agree.jsonl", flush=True)


def aux():
    """aux <tag | refs> [--k K] [--timeout S] [--workers W] [--ids file]: for each base translation (refs: $POC_DATA/geo/gt_refs.jsonl;
    a tag: the guarded, unproved rows of gt_<tag>_check.jsonl, optionally only the ids/samples listed in --ids as id:sample), DDAR on the
    translation alone, then with one auxiliary point at a time (aux_candidates, in order) until one proves -> gt_<tag>_aux.jsonl"""
    tag = sys.argv[2]
    arg = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
    k, timeout, workers = arg("--k", 64), arg("--timeout", 60.0), arg("--workers", 4)
    if tag == "refs":
        B = [json.loads(l) for l in open(os.path.join(PD, "gt_refs.jsonl"))]
    else:
        B = [r for r in map(json.loads, open(f"{OUT}/gt_{tag}_check.jsonl")) if r["status"] == "guarded" and not r["proved"]]
        if "--ids" in sys.argv:
            keep = set(open(sys.argv[sys.argv.index("--ids") + 1]).read().split())
            B = [r for r in B if f"{r['id']}:{r['sample']}" in keep]

    def one(dsl):
        try:
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "one", dsl, str(timeout)], capture_output=True, text=True,
                               timeout=timeout + 600)
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception as e:
            return ["build error", None, f"{type(e).__name__}", 0]

    prop = None
    if "--prop" in sys.argv:   # candidates proposed by the model (propose), in its order, samples interleaved; no DDAR-alone rerun
        prop = {}
        for q in map(json.loads, open(f"{OUT}/gt_{sys.argv[sys.argv.index('--prop') + 1]}_prop.jsonl")):
            prop.setdefault((q["id"], q["sample"]), []).append(q)
        B = [{"id": i, "sample": s, "dsl": v[0]["dsl"]} for (i, s), v in prop.items()]

    def cands_of(r):
        if prop is None:
            return aux_candidates(r["dsl"], k)
        pre, goal = r["dsl"].split(" ? ")
        _, x = aux_points(r["dsl"])
        qs = sorted(prop[(r["id"], r.get("sample", 0))], key=lambda q: q["s"])
        C = list(dict.fromkeys(c for j in range(max(len(q["cands"]) for q in qs)) for q in qs if j < len(q["cands"]) for c in [q["cands"][j]]))
        return [(c, f"{pre}; {x} = {c} ? {goal}") for c in C]

    def run(r):
        if prop is None:
            st, pr, msg, sec = one(r["dsl"])
        else:
            st, pr, msg, sec = "guarded", False, "", 0
        out = {"id": r["id"], "sample": r.get("sample", 0), "dsl": r["dsl"], "base": st, "base_proved": pr, "aux": None, "tried": 0,
               "sec": sec}
        if pr or st != "guarded":
            return out
        for c, d in cands_of(r):
            st2, pr2, _, s2 = one(d)
            out["tried"] += 1; out["sec"] += s2
            if pr2:
                out["aux"] = c
                break
        return out
    name = f"{tag}_auxp" if prop is not None else f"{tag}_aux"
    with ThreadPoolExecutor(workers) as ex, open(f"{OUT}/gt_{name}.jsonl", "w") as f:
        for fu in as_completed([ex.submit(run, r) for r in B]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(f"SIDE-GT aux {tag}: {len(B)} translations -> {OUT}/gt_{name}.jsonl", flush=True)


def one_lem(dsl, pts, lemmas, timeout, trace=False, proof=None):
    """SIDE-GT-POOL, one DDAR run in its own process: the translation dsl (possibly with auxiliary points) plus lemmas, which are facts
    ("name args") over the points pts that other runs proved. Returns whether the goal fell, the facts over pts this run holds as [hash,
    fact], the lemmas the proof uses, and how many lemmas were dropped because they fail on this figure (a run's facts hold on its own
    figure; a step with two intersections can take the other one here). With trace, also which lemmas each new fact rests on; with proof,
    the proof's steps are written to that file."""
    import time
    from pathlib import Path
    from newclid import GeometricSolverBuilder
    from newclid.defs.clause import Construction
    from newclid.dependencies.dependency import Reason
    from newclid.dependencies.dependency_building import DependencyBody
    from newclid.geometry import Point
    from newclid.numerical.check import check_numerical
    from newclid.statements.statement import Statement
    import newclid.numerical.check as nc
    nc.ATOM, nc.close_enough = 1e-7, (lambda a, b, tol=1e-7: abs(a - b) < tol)
    t0, facts, drop, err, inj, prov = time.time(), {}, 0, None, 0, {}

    def leaves(deps):
        seen, stack, out = set(), list(deps), set()
        while stack:
            d = stack.pop()
            if d is None or id(d) in seen:
                continue
            seen.add(id(d))
            if d.reason is not None and d.reason.name == "lemma":
                out.add(str(d.statement))
            elif d.reason is not None and d.reason.name.startswith("lemma:"):
                out.add(lemmas[int(d.reason.name[6:])])
            stack += list(d.why or ())
        return out
    for seed in map(int, os.environ.get("GT_DDAR_SEEDS", "0").split(",")):
        s = None
        try:
            s = GeometricSolverBuilder(seed=seed).load_problem_from_txt(dsl, translate=False).build()
            P = s.proof_state
            drop, inj = 0, 0
            for i, l in enumerate(lemmas):
                n, *a = l.split()
                try:
                    st = Statement(n, tuple(P.map_construction_args_to_objects(Construction(n, tuple(a), ()))))
                    if not num_holds(st):
                        drop += 1
                        continue
                    added, to_cache = P.resolve_statement_dependencies(st, DependencyBody(Reason(f"lemma:{i}" if trace else "lemma"), ()))
                except Exception:   # a lemma the figure cannot hold (degenerate here), like a failed numerical check
                    drop += 1
                    continue
                inj += 1
                P._init_added += added
                P._init_to_cache += to_cache
            proved, err = bool(s.run(timeout=timeout)), None
        except Exception as e:   # the facts derived before a mid-run failure stand; the next diagram may run clean
            proved, err = False, f"{type(e).__name__}"
        if s is None:
            continue
        P = s.proof_state
        for d in P.dependency_cache.cache.values():
            st = d.statement
            if st.predicate in P.statements.adder.PREDICATE_TO_ADDER and all(a.name in pts for a in st.args if isinstance(a, Point)):
                facts[" ".join(st.hash_tuple)] = str(st)
                if trace:
                    prov[" ".join(st.hash_tuple)] = sorted(leaves([d]))
        if err is None:
            used = leaves([P.statements.graph.build_resolved_dependency(g) for g in P.goals_as_statements()]) if proved else set()
            if proved and proof:
                s.write_solution(Path(proof))
            return {"proved": proved, "facts": list(facts.items()), "used": sorted(used), "drop": drop, "inj": inj, "err": None,
                    "sec": time.time() - t0, "prov": prov}
    return {"proved": False, "facts": list(facts.items()), "used": [], "drop": drop, "inj": inj, "err": err, "sec": time.time() - t0,
            "prov": prov}


def one_true(dsl, lemmas, n=8):
    """On how many of n fresh diagrams of the translation each lemma holds, numerically: an independent test of what a proof rests on"""
    from newclid import GeometricSolverBuilder
    from newclid.defs.clause import Construction
    from newclid.numerical.check import check_numerical
    from newclid.statements.statement import Statement
    import newclid.numerical.check as nc
    nc.ATOM, nc.close_enough = 1e-7, (lambda a, b, tol=1e-7: abs(a - b) < tol)
    held, built = {l: 0 for l in lemmas}, 0
    for seed in range(100, 100 + n):
        try:
            P = GeometricSolverBuilder(seed=seed, no_goal=True).load_problem_from_txt(dsl, translate=False).build().proof_state
        except Exception:
            continue
        built += 1
        for l in lemmas:
            k, *a = l.split()
            try:
                held[l] += num_holds(Statement(k, tuple(P.map_construction_args_to_objects(Construction(k, tuple(a), ())))))
            except Exception:
                pass
    return {"diagrams": built, "held": held}


def one_audit(dsl, lemmas, timeout):
    """SIDE-GT audit: rerun a proof and test every statement it uses, numerically, on its own figure and on fresh ones. A rule that is sound
    cannot derive a statement that fails on the figure it was derived on, so a failure there means the proof is not one."""
    from newclid import GeometricSolverBuilder
    from newclid.defs.clause import Construction
    from newclid.dependencies.dependency import Reason
    from newclid.dependencies.dependency_building import DependencyBody
    from newclid.numerical.check import check_numerical
    from newclid.statements.statement import Statement
    import newclid.numerical.check as nc
    nc.ATOM, nc.close_enough = 1e-7, (lambda a, b, tol=1e-7: abs(a - b) < tol)
    out = {"proved": False, "tries": 0, "errs": []}
    for seed in map(int, os.environ.get("GT_DDAR_SEEDS", "0,1,2,3,4,5").split(",")):
        out["tries"] += 1
        try:
            s = GeometricSolverBuilder(seed=seed).load_problem_from_txt(dsl, translate=False).build()
            P = s.proof_state
            for l in lemmas:
                n, *a = l.split()
                added, to_cache = P.resolve_statement_dependencies(Statement(n, tuple(P.map_construction_args_to_objects(Construction(n, tuple(a), ())))),
                                                                  DependencyBody(Reason("lemma"), ()))
                P._init_added += added
                P._init_to_cache += to_cache
            if not s.run(timeout=timeout):
                continue
        except Exception as e:
            out["errs"].append(type(e).__name__)
            continue
        P = s.proof_state
        seen, stack, deps = set(), [P.statements.graph.build_resolved_dependency(g) for g in P.goals_as_statements()], []
        while stack:
            d = stack.pop()
            if d is None or id(d) in seen:
                continue
            seen.add(id(d))
            deps.append(d)
            stack += list(d.why or ())
        st = {}
        for d in deps:
            st.setdefault(str(d.statement), d)
        out.update(proved=True, seed=seed, statements=len(st), roots=sorted(k for k, d in st.items() if not d.why and (d.reason is None or d.reason.name != "lemma")))
        nc.ATOM, nc.close_enough = 1e-4, (lambda a, b, tol=1e-4: abs(a - b) < tol)   # false by far more than rounding
        bad = []
        for k, d in st.items():
            try:
                if d.statement.predicate.value in ("ncoll", "npara", "sameclock", "sameside", "diff", "ind") or num_holds(d.statement, 1e-4):
                    continue
            except Exception:
                continue
            bad.append(k)
        out["false_on_own_figure"] = sorted(bad)
        # the same statements on fresh diagrams, with the proof's own goal required to hold there, so that a two-intersection branch is not blamed
        fresh, built = {k: 0 for k in st}, 0
        for seed2 in range(100, 108):
            try:
                Q = GeometricSolverBuilder(seed=seed2, no_goal=True).load_problem_from_txt(dsl, translate=False).build().proof_state
                g = Construction.from_txt(dsl.split(" ? ")[1].strip())
                if not num_holds(Statement(g.name, Q.map_construction_args_to_objects(g)), 1e-4):
                    continue
            except Exception:
                continue
            built += 1
            for k in st:
                n, *a = k.split()
                try:
                    fresh[k] += num_holds(Statement(n, tuple(Q.map_construction_args_to_objects(Construction(n, tuple(a), ())))), 1e-4)
                except Exception:
                    fresh[k] += 1   # a statement this figure cannot evaluate is not counted against the proof
        out["fresh_diagrams"] = built
        out["false_on_fresh"] = sorted(k for k, v in fresh.items() if built and v < built)
        out["fresh_counts"] = {k: fresh[k] for k in out["false_on_fresh"]}
        # a statement the proof uses with no reason must be a construction fact: one the state holds before any deduction
        Q, unj = GeometricSolverBuilder(seed=seed, no_goal=True).load_problem_from_txt(dsl, translate=False).build().proof_state, []
        Q.reset()
        for k in out["roots"]:
            n, *a = k.split()
            if n in ("ncoll", "npara", "sameclock", "sameside", "diff", "ind"):
                continue
            try:
                if not Q.check(Statement(n, tuple(Q.map_construction_args_to_objects(Construction(n, tuple(a), ()))))):
                    unj.append(k)
            except Exception:
                unj.append(k)
        out["unjustified_roots"] = unj
        return out
    return out


def audit():
    """audit <list.jsonl> <out.jsonl> [--timeout S] [--workers W]: each row {"id", "sample", "arm", "dsl", "lem"} -> one_audit"""
    arg = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
    timeout, workers = arg("--timeout", 120.0), arg("--workers", 16)
    R = [json.loads(l) for l in open(sys.argv[2])]

    def run(r):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            json.dump(r.get("lem", []), f); f.flush()
            try:
                p = subprocess.run([sys.executable, os.path.abspath(__file__), "one_audit", r["dsl"], str(timeout), f.name], capture_output=True, text=True,
                                   timeout=timeout * 6 + 900)
                return {**r, **json.loads(p.stdout.strip().splitlines()[-1])}
            except Exception as e:
                return {**r, "proved": False, "errs": [type(e).__name__]}
    with ThreadPoolExecutor(workers) as ex, open(sys.argv[3], "w") as f:
        for fu in as_completed([ex.submit(run, r) for r in R]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()


def rename_aux(c, x, new):
    return " ".join(new if w == x else w for w in c.split())


def pool():
    """pool <tag | refs> [--k K] [--timeout S] [--workers W] [--rounds R] (SIDE-GT-POOL): for each translation of a problem that no single
    random point proved (gt_<tag>_aux.jsonl), DDAR with each of the same k points, one at a time, keeping every fact a run proves over the
    translation's own points. The union goes back in as lemmas on the translation alone; if the goal does not fall, each point runs again
    with the lemmas, and so on. A proof that uses lemmas from several points is confirmed by plain DDAR with those points added together.
    -> gt_<tag>_pool.jsonl. With --pairs: instead k random pairs of points added together -> gt_<tag>_pair.jsonl (the comparison).
    With --alone: as registered, a round's runs get only the previous rounds' lemmas (the default also passes those of the same round, run
    by run) -> gt_<tag>_poolA.jsonl. --alone and --cert (the default's order, -> gt_<tag>_poolC.jsonl; --only keeps the translations
    gt_<tag>_pool.jsonl proved) also record what each fact rests on and check each proof: every step replayed with only the lemmas it
    needs, the lemmas tested on fresh diagrams, plain DDAR with all the points it needed."""
    import random, tempfile
    tag = sys.argv[2]
    arg = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
    k, timeout, workers, rounds, confirm = arg("--k", 64), arg("--timeout", 60.0), arg("--workers", 16), arg("--rounds", 2), arg("--confirm", 600.0)
    R = [json.loads(l) for l in open(f"{OUT}/gt_{tag}_aux.jsonl")]
    done = {r["id"] for r in R if r["aux"] or r["base_proved"]}
    if os.path.exists(f"{OUT}/gt_{tag}_check.jsonl"):   # a problem DDAR alone proved from a translation that counts (--ids) is done too
        ids = set(open(sys.argv[sys.argv.index("--ids") + 1]).read().split()) if "--ids" in sys.argv else None
        done |= {q["id"] for q in map(json.loads, open(f"{OUT}/gt_{tag}_check.jsonl")) if q.get("proved") and (ids is None or f"{q['id']}:{q['sample']}" in ids)}
    B = [r for r in R if r["id"] not in done and r["base"] == "guarded"]
    alone, cert = "--alone" in sys.argv, "--alone" in sys.argv or "--cert" in sys.argv
    if "--only" in sys.argv:
        keep = {(q["id"], q["sample"]) for q in map(json.loads, open(f"{OUT}/gt_{tag}_pool.jsonl")) if q["proved"]}
        B = [r for r in B if (r["id"], r["sample"]) in keep]
    if "--limit" in sys.argv:
        B = B[:arg("--limit", 0)]

    def call(dsl, pts, lem, proof=None):
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            json.dump({"pts": pts, "lem": lem, "trace": cert, "proof": proof}, f); f.flush()
            try:
                p = subprocess.run([sys.executable, os.path.abspath(__file__), "one_lem", dsl, str(timeout), f.name], capture_output=True,
                                   text=True, timeout=timeout + 600)
                return json.loads(p.stdout.strip().splitlines()[-1])
            except Exception as e:
                return {"proved": False, "facts": [], "used": [], "drop": 0, "inj": 0, "err": type(e).__name__, "sec": 0}

    def plain(dsl, t):
        try:   # no step limit (Newclid's default of 10,000 steps stops a run at 30-80 s whatever the time limit), for the long confirmations
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "one", dsl, str(t)], capture_output=True, text=True, timeout=t + 600,
                               env={**os.environ, "GT_MAX_STEPS": str(10 ** 8 if t > timeout else 10000)})
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception as e:
            return ["build error", None, type(e).__name__, t]

    def certify(r, pts, x, pre, goal, used, last, src, rest, by_call, lem):
        hof = {f: h for h, f in lem.items()}
        need, stack = set(), list(used)
        while stack:
            u = stack.pop()
            if u not in need:
                need.add(u)
                stack += rest.get(u, [])
        calls = sorted({by_call[u] for u in need if u in by_call})
        steps = []
        for cid in calls:
            c, d = cid[1], cid[2]
            mine = [u for u in need if by_call.get(u) == cid]
            lem = sorted({v for u in mine for v in rest.get(u, [])})
            q = call(d, pts, lem)
            got = {h for h, _ in q["facts"]} | {hof[v] for v in lem}
            miss = [u for u in mine if hof[u] not in got]
            steps.append({"point": c, "lemmas_in": len(lem), "facts_needed": len(mine), "missing": miss, "err": q["err"], "sec": round(q["sec"], 1)})
        os.makedirs(f"{OUT}/pool_proofs", exist_ok=True)
        lastc = [] if last is None else [last[0]]
        if last is None:
            fin = call(r["dsl"], pts, sorted(need), proof=f"{OUT}/pool_proofs/{tag}_{r['id']}_{r['sample']}.txt")
        else:
            fin = call(last[1], pts, sorted(need), proof=f"{OUT}/pool_proofs/{tag}_{r['id']}_{r['sample']}.txt")
        P = sorted({s["point"] for s in steps} | set(lastc))
        names = [f"{x}{i}" for i in range(len(P))]
        d = f"{pre}; " + "; ".join(f"{n} = {rename_aux(c, x, n)}" for n, c in zip(names, P)) + f" ? {goal}"
        st, pr, msg, sec = plain(d, confirm)
        tr = {"diagrams": 0, "held": {}}
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
                json.dump(sorted(need), f); f.flush()
                tr = json.loads(subprocess.run([sys.executable, os.path.abspath(__file__), "one_true", r["dsl"], f.name], capture_output=True,
                                               text=True, timeout=1200).stdout.strip().splitlines()[-1])
        except Exception as e:
            tr["err"] = type(e).__name__
        return {"points": P, "lemmas": sorted(need), "steps": steps, "final": fin["proved"], "final_used": len(fin["used"]), "final_err": fin["err"],
                "true_on": tr, "joint_dsl": d, "joint_status": st, "joint_proved": pr, "joint_msg": msg, "joint_sec": round(sec, 1)}

    def run_pair(r):
        pts, x = aux_points(r["dsl"])
        pre, goal = r["dsl"].split(" ? ")
        C, rng = [c for c, _ in aux_candidates(r["dsl"], k)], random.Random(1)
        out = {"id": r["id"], "sample": r["sample"], "dsl": r["dsl"], "aux": None, "tried": 0, "sec": 0}
        for _ in range(k):
            a, b = rng.sample(C, 2)
            d = f"{pre}; {x}0 = {rename_aux(a, x, x + '0')}; {x}1 = {rename_aux(b, x, x + '1')} ? {goal}"
            st, pr, _, s2 = plain(d, timeout)
            out["tried"] += 1; out["sec"] += s2
            if pr:
                out["aux"] = [a, b]
                break
        return out

    def run(r):
        pts, x = aux_points(r["dsl"])
        pre, goal = r["dsl"].split(" ? ")
        C = aux_candidates(r["dsl"], k)
        out = {"id": r["id"], "sample": r["sample"], "dsl": r["dsl"], "proved": False, "round": None, "via": None, "used_aux": None, "rounds": [],
               "calls": 1, "sec": 0}
        b = call(r["dsl"], pts, [])
        out["sec"] += b["sec"]
        known, src, lem, rest, by_call, ncall = {h for h, _ in b["facts"]}, {}, {}, {}, {}, 0
        for rd in range(1, rounds + 1):
            info = {"round": rd, "with_new": 0, "new": 0, "errs": 0, "drop": 0}
            given = list(lem.values())
            for c, d in C:
                ncall += 1
                q = call(d, pts, given if alone else list(lem.values()))
                out["calls"] += 1; out["sec"] += q["sec"]
                info["errs"] += q["err"] is not None
                info["drop"] += q["drop"]
                new = [(h, f) for h, f in q["facts"] if h not in known and h not in lem]
                info["with_new"] += bool(new)
                for h, f in new:
                    lem[h] = f
                    src[f] = c
                    if cert:
                        rest[f], by_call[f] = q["prov"].get(h, []), (ncall, c, d)
                info["new"] += len(new)
                if q["proved"]:   # one point plus the lemmas (round 2 on; in round 1 the single-point arm would have found it)
                    out.update(proved=True, round=rd, via="point+lemmas", used_aux=sorted({c} | {src.get(u, "?") for u in q["used"]}))
                    if cert:
                        out["cert"] = certify(r, pts, x, pre, goal, q["used"], (c, d), src, rest, by_call, lem)
                    break
            out["rounds"].append(info)
            if not out["proved"]:
                q = call(r["dsl"], pts, list(lem.values()))
                out["calls"] += 1; out["sec"] += q["sec"]
                info.update(pool=len(lem), pool_drop=q["drop"], pool_sec=q["sec"], pool_err=q["err"])
                if q["proved"]:
                    out.update(proved=True, round=rd, via="pool", used_aux=sorted({src.get(u, "?") for u in q["used"]}))
                    if cert:
                        out["cert"] = certify(r, pts, x, pre, goal, q["used"], None, src, rest, by_call, lem)
            if out["proved"] or not info["new"]:   # proved, or a fixed point: another round cannot change anything
                break
        if out["proved"] and not cert:
            U = [c for c in out["used_aux"] if c != "?"]
            names = [f"{x}{i}" for i in range(len(U))]
            d = f"{pre}; " + "; ".join(f"{n} = {rename_aux(c, x, n)}" for n, c in zip(names, U)) + f" ? {goal}"
            st, pr, _, sec = plain(d, confirm)
            out.update(joint_dsl=d, joint_status=st, joint_proved=pr, joint_sec=sec)
        return out
    name, fn = (f"{tag}_pair", run_pair) if "--pairs" in sys.argv else (f"{tag}_pool" + ("A" if alone else "C" if cert else ""), run)
    with ThreadPoolExecutor(workers) as ex, open(f"{OUT}/gt_{name}.jsonl", "w") as f:
        for fu in as_completed([ex.submit(fn, r) for r in B]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(f"SIDE-GT pool {tag}: {len(B)} translations -> {OUT}/gt_{name}.jsonl", flush=True)


def deep(fn):
    """Runs fn with a large stack and prints its result: Newclid deep-copies the proof state at the start of a run, which recurses through the
    whole graph, and a state with injected lemmas exceeds Python's default depth (RecursionError)"""
    import threading
    sys.setrecursionlimit(10 ** 6)
    threading.stack_size(2 ** 30)
    out = []
    t = threading.Thread(target=lambda: out.append(fn()))
    t.start()
    t.join()
    print(json.dumps(out[0]))


if __name__ == "__main__":
    if sys.argv[1] == "one":
        import logging
        logging.disable(logging.CRITICAL)
        patch_newclid()
        deep(lambda: one_check(sys.argv[2], float(sys.argv[3])))
    elif sys.argv[1] == "one_lem":
        import logging
        logging.disable(logging.CRITICAL)
        patch_newclid()
        q = json.load(open(sys.argv[4]))
        deep(lambda: one_lem(sys.argv[2], set(q["pts"]), q["lem"], float(sys.argv[3]), q.get("trace", False), q.get("proof")))
    elif sys.argv[1] == "one_audit":
        import logging
        logging.disable(logging.CRITICAL)
        patch_newclid()
        q = json.load(open(sys.argv[4]))
        deep(lambda: one_audit(sys.argv[2], q, float(sys.argv[3])))
    elif sys.argv[1] == "one_true":
        import logging
        logging.disable(logging.CRITICAL)
        print(json.dumps(one_true(sys.argv[2], json.load(open(sys.argv[3])))))
    elif sys.argv[1] == "one_agree":
        import logging
        logging.disable(logging.CRITICAL)
        print(json.dumps(one_agree(sys.argv[2], sys.argv[3])))
    else:
        {"gen": gen, "check": check, "aux": aux, "propose": propose, "agree": agree, "pool": pool, "audit": audit}[sys.argv[1]]()
