"""COMP-FIG (docs/prereg/PREREG_FIG.md): the model describes a geometry problem as a figure and computes nothing. One script from the model; figlib.py finds figures by least squares and
reads the answer on each. A script with no figure, an error, or an answer that changes between figures gets its message back once (a free check); an answer the same on every figure is
the answer. Grading uses the gold answer only to score.
  POC_BASE_URL=... python poc/run_fig.py <tag> <set> <seed> [--think] [--max_tokens N] [--repair R] [--workers W] [--solvers S]     sets: dev | held
  -> results/x1/fig_<tag>_<set>_s<seed>.jsonl: id, src, gold, code, status, values, answer, correct, out_tokens, turns, trace"""
import csv, json, os, re, resource, subprocess, sys, tempfile, threading, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_msgs, last_block  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "results", "x1")
KW = re.compile(r"triangle|circle|square|rectangle|hexagon|polygon|trapezoid|rhomb|parallelogram|tangent|chord|perpendicular|sphere|diagonal|pentagon|octagon|cube|tetrahedron|pyramid|cylinder|cone|torus|prism|\bangle\b|\bquadrilateral\b", re.I)

MANUAL = r"""Describe this geometry problem as a figure, in a short Python script. Do NOT solve it and do no algebra: a solver finds the coordinates, and your script only states what is given and what is asked.

Declare the unknowns, then state every condition:
  A, B, C = points("A B C")      # points in the plane, with unknown coordinates; points("P Q", dim=3) in space. Different names are different points.
  r = var("r")                    # an unknown number (a radius, a length, a ratio)
Values: dist(A,B), angle(A,B,C) (degrees, at B, between 0 and 180), area(A,B,C,...) (polygon in order), perimeter(A,B,C,...), volume(A,B,C,D), dot(u,v), sqrt(x), pi, sin/cos/tan (degrees). Points are vectors: A+B, (A+B)/2, B-A work.
Built points (give a point, no condition needed): midpoint(A,B), foot(P,A,B), reflect(P,A,B) (over line AB), intersection(A,B,C,D) (of lines), centroid(A,B,C), incenter(A,B,C), circumcenter(A,B,C). inradius(A,B,C), circumradius(A,B,C) give numbers.
Conditions: eq(x,y), gt(x,y), lt(x,y), perp(A,B,C,D), parallel(A,B,C,D), collinear(A,B,C), between(P,A,B) (P strictly inside segment AB), on_ray(P,A,B), on_circle(P,O,r), concyclic(A,B,C,D), tangent_line(A,B,O,r) (line AB tangent to the circle), tangent_circles(O1,r1,O2,r2) (externally), tangent_inside(O1,r1,O2,r2) (circle 2 inside circle 1), same_side(P,Q,A,B), opposite_side(P,Q,A,B), inside(P,A,B,C,...), convex(A,B,C,...), parallelogram(A,B,C,D), rectangle(A,B,C,D), rhombus(A,B,C,D), square(A,B,C,D), regular(A,B,C,...) (vertices in order).
End with answer(x): the number the problem asks for. If it asks for m+n with the value written m/n, use frac: m, n = frac(x); answer(m+n). For m*sqrt(n)/p use m, n, p = surd(x). For (a+b*sqrt(n))/d use a, b, n, d = surd2(x). Use these only on the final value.

Every sentence of the problem must become a condition, including order: "E is on side AB" is between(E,A,B), "ABCD is convex" is convex(A,B,C,D), and "acute", "inside", "on the same side" must be stated. The solver picks at random among all figures your conditions allow, so a condition you leave out gives a wrong or changing answer. If a problem says "for all" or asks for an extreme value, write the figure that attains it only when the problem tells you which it is. If the problem is not a single figure with a number to read off (counting, a sum over many cases), reply with only the word UNEXPRESSIBLE.

Example. "In triangle ABC, AB=13, BC=14, CA=15. D is on BC with AD perpendicular to BC. Find BD."
```python
A, B, C, D = points("A B C D")
eq(dist(A,B), 13); eq(dist(B,C), 14); eq(dist(C,A), 15)
between(D, B, C)
perp(A, D, B, C)
answer(dist(B, D))
```
Example. "Circles of radius 1 and 2 are externally tangent, and a line touches both at P and Q. PQ^2 is m/n with m, n coprime. Find m+n."
```python
O1, O2, P, Q = points("O1 O2 P Q")
tangent_circles(O1, 1, O2, 2)
on_circle(P, O1, 1); on_circle(Q, O2, 2)
perp(O1, P, P, Q); perp(O2, Q, P, Q)
same_side(O1, O2, P, Q)
m, n = frac(dist(P, Q)**2)
answer(m + n)
```

Problem: {p}

Give the script in one ```python block."""

USE = """Exact use: points("A B") returns points; eq(x,y) takes two values or two points; foot(P,A,B), midpoint(A,B), intersection(A,B,C,D), reflect(P,A,B) RETURN a point (write D = foot(C,A,B) and do not list D in points()); volume takes 4 points; dist, angle, area and perimeter take points, not numbers. There is no solve() and no other function: state conditions and let the solver work."""
MSG = {"err": "The script failed: {msg}. " + USE + " Give the whole script again.",
       "const": "Your answer does not read the figure: it stays the same on any points at all. answer() must use dist, angle, area and so on of the points you declared. If the problem is not a figure with a number to read off, reply with only the word UNEXPRESSIBLE.",
       "nonint": "The value {values} is not an integer, and this contest's answers are integers from 0 to 999. So the value is right only if the problem asks for a form of it: use frac, surd or surd2 as the statement says, and answer the number it asks for. If the value itself looks wrong, compare the conditions with the statement.",
       "none": "No figure satisfies these conditions: the solver tried {starts} random starts. A condition is wrong, or two conflict. Compare each one with the statement and fix the script.",
       "multi": "The conditions allow different answers: {values}. So a condition is missing, or an order or side is not stated. Compare with the statement and add what is missing, without solving the problem."}
SOLVERS = threading.Semaphore(int(os.environ.get("FIG_SOLVERS", 4)))


def problems(which):
    if which == "held":
        rows = list(csv.DictReader(open(os.path.join(os.environ.get("POC_DATA", ""), "aime", "aime.csv"), encoding="utf-8")))
        return [dict(id=f"aime-{r['ID']}", src="aime", problem=r["Question"], answer=str(int(r["Answer"]))) for r in rows if int(r["Year"]) < 2024 and KW.search(r["Question"]) and "[asy]" not in r["Question"]]
    D = json.load(open(f"{RES}/problems.json"))
    out = [dict(id=str(r["id"]), src="math500", problem=r["problem"], answer=str(r["answer"])) for r in D["math500"] if r["subject"] == "Geometry" and "[asy]" not in r["problem"]]
    return out + [dict(id=str(r["id"]), src=s, problem=r["problem"], answer=str(r["answer"])) for s in ("aime24", "aime25") for r in D[s] if KW.search(r["problem"]) and "[asy]" not in r["problem"]]


def limits():
    os.setsid()
    resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 << 20, 16 << 20))


def solve(code, budget):
    with SOLVERS, tempfile.TemporaryDirectory(prefix="fig_") as d:
        path = os.path.join(d, "s.py")
        open(path, "w").write(code)
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
        try:
            p = subprocess.run([sys.executable, os.path.join(HERE, "figlib.py"), path, "--budget", str(budget)], capture_output=True, text=True, timeout=budget + 30, cwd=d, env=env, preexec_fn=limits)
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception as e:
            return dict(status="err", values=[], figures=0, starts=0, msg=f"the solver stopped: {type(e).__name__}"[:200], sec=budget)


def gold_value(g):
    """the gold answer as a number, or None"""
    g = g.strip().strip("$").replace("\\dfrac", "\\frac").replace("^\\circ", "").replace("\\%", "").replace("\\!", "").replace(",", "")
    try:
        return float(g)
    except ValueError:
        pass
    try:
        from math_verify import parse
        for e in parse(f"${g}$"):
            try:
                return float(e.evalf())
            except Exception:
                continue
    except Exception:
        pass
    return None


def right(v, g):
    return g is not None and v is not None and abs(float(v) - g) <= 1e-5 * max(1.0, abs(g))


def main():
    a = sys.argv
    tag, which, seed = a[1], a[2], int(a[3])
    arg = lambda n, d: type(d)(a[a.index(n) + 1]) if n in a else d
    think, mt, repair, workers, budget = "--think" in a, arg("--max_tokens", 2000), arg("--repair", 1), arg("--workers", 16), arg("--budget", 40.0)
    P = problems(which)
    G = {p["id"]: gold_value(p["answer"]) for p in P}  # here, in the main thread: math_verify's timeout is a signal
    print("gold answers with no number:", [p["answer"] for p in P if G[p["id"]] is None], flush=True)
    path = f"{RES}/fig_{tag}_{which}_s{seed}.jsonl"
    done = set()
    if os.path.exists(path):
        for l in open(path, errors="replace"):
            try:
                done.add(json.loads(l)["id"])
            except ValueError:
                pass
    print(f"fig {tag} {which} s{seed}: {len(P)} problems, {len(P) - len(done)} left", flush=True)

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        msgs, toks, trace, code, res, turns = [dict(role="user", content=MANUAL.replace("{p}", p["problem"]))], 0, [], None, dict(status="unexpressible", values=[]), 0
        for t in range(repair + 1):
            o = chat_msgs(msgs, think=think, max_tokens=mt, temperature=0.7, seed=sd + t)
            text, turns = o["text"] or "", t + 1
            toks += o.get("out_tokens") or 0
            code = last_block(text, ("python", "py", "python3"))
            if not code:
                res = dict(status="unexpressible" if "UNEXPRESSIBLE" in text else "nocode", values=[])
                trace.append(dict(status=res["status"], tail=text[-200:]))
                break
            res = solve(code, budget)
            if res["status"] == "inv" and p["src"].startswith("aime") and not (abs(res["values"][0][0] - round(res["values"][0][0])) < 1e-6 and 0 <= round(res["values"][0][0]) <= 999):
                res["status"] = "nonint"  # the contest's own rule, a free check; not an answer
            trace.append(dict(code=code, **res))
            if res["status"] == "inv" or t == repair:
                break
            msgs += [dict(role="assistant", content=f"```python\n{code}\n```"), dict(role="user", content=MSG[res["status"]].format(msg=res.get("msg", ""), starts=res.get("starts", 0), values=[round(v[0], 6) for v in res.get("values", [])][:4]))]
        v = res["values"][0][0] if res["status"] == "inv" else None
        return dict(id=p["id"], src=p["src"], gold=p["answer"], status=res["status"], answer=v, correct=right(v, G[p["id"]]), figures=res.get("figures"), out_tokens=toks, turns=turns, code=code, trace=trace, sec=res.get("sec"))

    lock = threading.Lock()
    with ThreadPoolExecutor(workers) as ex, open(path, "a") as f:
        def job(p):
            r = one(p)
            with lock:
                f.write(json.dumps(r) + "\n")
                f.flush()
            return r
        rows = list(ex.map(job, [p for p in P if p["id"] not in done]))
    all_rows = [json.loads(l) for l in open(path, errors="replace")]
    st = {}
    for r in all_rows:
        k = r["status"]
        st.setdefault(k, [0, 0])
        st[k][0] += 1
        st[k][1] += bool(r["correct"])
    print(tag, which, seed, st, f"right {sum(bool(r['correct']) for r in all_rows)}/{len(all_rows)}", f"tokens {sum(r['out_tokens'] for r in all_rows) / max(1, len(all_rows)):.0f}", flush=True)


if __name__ == "__main__":
    main()
