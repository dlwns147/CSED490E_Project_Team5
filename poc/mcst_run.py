"""MCST (PREREG_DIFF, 2026-11-28): transfer test of the MathConstruct recipe OWN-EF-GJ to a second, recent construction benchmark,
MathConstraint (Pati et al., 2605.08498; 329 solver-verified combinatorial CSP instances, 39 types, 228 SAT / 101 UNSAT). Nothing is re-tuned:
OWN-EF = the native python tool + the installed-solver sentence + submit(s) with the solver's own check (TS.TAIL + TS.OWN) + a format-only check
at submit (≤ FMT_TRIES resubmissions); GJ = a second OWN-EF attempt only when the first used > 7,536 generated tokens (τ fitted on MathConstruct,
unchanged) and a code-running judge between the two. Arms written here:
  TIR    plain native tool, answer in \\boxed{} (the TIR-N baseline: Nemotron-Math 2512.15489 style)
  OWNEF  the recipe's single attempt
  judge  the code-running judge between two OWNEF seeds (all differing pairs, so the gate can be read for every τ; only gated pairs are charged)
The paper's own harness (their prompt, JSON tools, 8 rounds) is run with their CLI (lane mcst6), not here.
Answer interface (both arms): the box / submission holds the solution as a JSON list in the shape the problem asks for, or the word UNSATISFIABLE.
Grading is not done here (the verifier needs pycsp3 + Java): poc/mcst_grade.py adds `correct` with the benchmark's validate_answer.
The sandbox python is the runner's own interpreter (/root/venvs/mcsbx: numpy, scipy, sympy, ortools, python-sat, z3, pycosat; no pycsp3, no benchmark code).
usage: TIR_ENV=1 POC_BASE_URL=... MCST_DATA=<problems.jsonl> python mcst_run.py run <TIR|OWNEF> <seed> | judge <sa> <sb>
-> results/x44/mcst_<arm>_s<seed>.jsonl, results/x44/mcst_judge_s<sa>_<sb>.jsonl
Temporary files: every attempt's sandbox directory is removed by Tool.close() / Session.close() in a finally block."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
assert os.environ.get("TIR_ENV"), "set TIR_ENV=1 (installed-solver sentence)"
import tir_native as T
import tir_submit as TS
R = T.R; FMT_TRIES = int(os.environ.get("FMT_TRIES", 2))
OLD_ENV = " The environment has numpy, scipy, sympy and ortools (Google OR-Tools, including the CP-SAT solver) installed."
NEW_ENV = (" The environment has numpy, scipy, sympy, ortools (Google OR-Tools, including the CP-SAT solver), python-sat (pysat), z3 and pycosat installed.")
assert OLD_ENV in T.SYS; T.SYS = T.SYS.replace(OLD_ENV, NEW_ENV)      # the same sentence, naming what is installed in this sandbox (the paper's tool also offers pysat, z3, pycosat)
from tir_dispute import Session                                        # imported after the patch: Session reads T.SYS at call time
FMT = ("\n\nAnswer format: the solution as a JSON list of integers in the shape the problem asks for (a list of [u, v] pairs for a graph), "
       "or the single word UNSATISFIABLE if no solution exists.")


def problems():
    return [json.loads(l) for l in open(os.environ.get("MCST_DATA", "/dev/shm/sj_nlp/mcst/Math-Constraint/mathconstraint/problems.jsonl"))]


def fmt_error(s):
    """format only: UNSATISFIABLE, or a JSON list whose leaves are integers. No value is checked."""
    s = s.strip()
    if re.fullmatch(r"(?i)\W*unsatisfiable\W*", s):
        return None
    try:
        v = json.loads(s)
    except Exception as e:
        return f"not valid JSON ({str(e)[:120]})"
    if not isinstance(v, list) or not v:
        return "not a non-empty JSON list"
    def leaves(x):
        return [y for z in x for y in leaves(z)] if isinstance(x, list) else [x]
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in leaves(v)):
        return "the list contains entries that are not integers"
    return None


def solve_own(q, effort, seed):
    """tir_submit_fmt.solve with the MathConstraint format check in place of Problem.parse (else unchanged)"""
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    q = q + FMT + TS.TAIL + TS.OWN
    ids = tok(T.SYS.format(e=effort, q=q)); used = calls = 0; seen_subs = 0; fmt_log = []; tool = T.Tool(); open(tool.f, "w").write(TS.T_DRIVER); subs = []; msgs = 0; fin = "stop"; text = ""; final = ""; codes = []; outs = []
    subf = os.path.join(tool.d.name, "subs.jsonl"); pre = TS.PRE.format(code=repr(""), code2=repr(""), enf=False, sub=repr(subf)); inited = None
    add = lambda xs: ids.extend(xs)
    try:
        while True:
            room = min(T.CAP - used, int(os.environ.get("TIR_CTX", 64000)) - len(ids) - 8)
            if room < 16:
                fin = "length"; break
            r = llm.client.completions.create(model="local", prompt=ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=seed + calls, extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            c = r.choices[0]; g = list(c.token_ids); used += r.usage.completion_tokens; text = c.text or ""; fin = c.finish_reason
            if fin == "length":
                break
            if T.CALL not in (g[-1] if g else None, c.stop_reason):
                msgs += 1
                if msgs > 3:
                    add(g); break
                base = g[:-1] if g and g[-1] == T.RET else g
                add(base); add(tok("<|end|><|start|>user<|message|>Your answer was not submitted. Call submit(s) in the python tool with the text that goes inside the box, built by your code from a value it computed.<|end|><|start|>assistant")); continue
            if g[-1] != T.CALL:
                g.append(T.CALL)
            m = text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]; calls += 1
            if calls > 200:
                fin = "calls"; break
            if tool.p is None or tool.p is not inited or tool.p.poll() is not None:
                tool.run(pre); inited = tool.p
            o = tool.run(code) if "python" in head else "Unknown tool. Only python is available."
            codes.append(code[:3000]); outs.append(o[:300]); add(g)
            subs = [json.loads(l) for l in open(subf)] if os.path.exists(subf) else []
            newf = [x for x in subs[seen_subs:] if x["final"]]
            if newf:
                cand = newf[0]["s"]; seen_subs = len(subs); err = fmt_error(cand)
                fmt_log.append({"s": cand[:300], "error": err})
                if err is None or len(fmt_log) > FMT_TRIES:
                    final = cand; fin = "submitted"; break
                tool.run("_S['done'] = False")          # let the session submit again (hidden from the model)
                o = ("FORMAT ERROR: the answer parser could not read this submission (" + err[:300] + "). This says nothing about whether the object is correct. "
                     "Rebuild s in exactly the required format and call submit(s) again.")
            add(tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + tok(o) + tok("<|end|><|start|>assistant"))
    finally:
        tool.close()
    if not final:
        t = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
        b = re.findall(r"\\boxed\{(.*)\}", t, re.S)
        final = b[-1] if b else (subs[-1]["s"] if subs else "")
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "fmt": fmt_log, "codes": codes, "outs": outs}


def solve_tir(q, effort, seed):
    z = T.solve(q + FMT + "\n\nPut the final answer alone in \\boxed{}.", effort, seed)
    b = re.findall(r"\\boxed\{(.*)\}", z.get("final") or "", re.S); z["final"] = b[-1] if b else ""
    return z


def run(arm, seed):
    path = f"{R}/mcst_{arm}_s{seed}.jsonl"; done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
    f_ = {"OWNEF": solve_own, "TIR": solve_tir}[arm]

    def one(p):
        try:
            z = f_(p["prompt"], "medium", seed * 1000 + zlib.crc32(p["name"].encode()) % 997)
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200]}
        z["id"] = p["name"]; z["final"] = (z.get("final") or "")[-6000:]; z["codes"] = [c[:3000] for c in z.get("codes", [])]; z["outs"] = [o[:300] for o in z.get("outs", [])]
        return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in problems()[:int(os.environ.get("MCST_N", 0)) or None] if p["name"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"MCST {arm} s{seed}: {len(Z)} rows @ {sum(z['out_tokens'] for z in Z)/len(Z)/1000:.2f}k; finish {dict((k, sum(z['finish'] == k for z in Z)) for k in set(z['finish'][:8] for z in Z))}", flush=True)


JQ = ("{p}\n\nTwo candidate answers have been submitted for this problem. A candidate may be the word UNSATISFIABLE, which claims that no solution exists.\n\nCandidate A:\n{a}\n\nCandidate B:\n{b}\n\n"
      "Exactly one of them may be correct. Determine which one is correct; you may use the python tool to test the conditions. Reply with the single letter of the correct candidate in \\boxed{{}}.")


def judge(sa, sb):
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    L = lambda s: {z["id"]: z for z in map(json.loads, open(f"{R}/mcst_OWNEF_s{s}.jsonl"))}
    A, B = L(sa), L(sb); P = {p["name"]: p for p in problems()}; out = f"{R}/mcst_judge_s{sa}_{sb}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    norm = lambda s: re.sub(r"\s+", "", s or "").upper()

    def one(k):
        p, a, b = P[k], A[k], B[k]; h = zlib.crc32(k.encode()); swap = h % 2 == 1; first, second = (b, a) if swap else (a, b)
        if norm(a["final"]) == norm(b["final"]):
            return {"id": k, "same": True, "out_tokens": 0, "swap": swap}
        s = Session(JQ.format(p=p["prompt"], a=first["final"][-3000:] or "(no answer)", b=second["final"][-3000:] or "(no answer)"), "medium", 31000 + h % 997, tok)
        try:
            f = s.gen(T.CAP)
        finally:
            s.close()
        m = re.findall(r"\\boxed\{\s*\(?([AB])\)?\s*\}", f or ""); letter = m[-1] if m else ""
        chosen = {"A": first, "B": second}.get(letter)
        return {"id": k, "same": False, "swap": swap, "letter": letter, "chosen_seed": (sb if chosen is b else sa) if chosen else None, "out_tokens": s.used, "calls": s.calls, "finish": s.fin}
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(out, "a") as fo:
        for fu in as_completed([ex.submit(one, k) for k in sorted(set(A) & set(B) & set(P)) if k not in done]):
            fo.write(json.dumps(fu.result()) + "\n"); fo.flush()
    print("MCST judge rows", sum(1 for _ in open(out)), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], int(sys.argv[3]))
    elif sys.argv[1] == "judge":
        judge(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "fmttest":
        for s in ("UNSATISFIABLE", "[1, 2, 3]", "[[0, 1], [1, 2]]", "[1, 2.5]", "x = [1,2]", "[]", "[true, 1]"):
            print(repr(s), "->", fmt_error(s))
