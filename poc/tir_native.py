"""PREREG_DIFF addendum TIR-N (2026-11-25): tool-integrated reasoning with gpt-oss-120b's NATIVE python tool (stateful, in the analysis channel, the system text it was trained with) on every computation set:
the recent-research baseline (Nemotron-Math 2512.15489 uses exactly this mode; ReTool 2504.11536, SimpleTIR 2509.02479, "Dissecting TIR" 2508.15754). Generated tokens of every turn are charged; tool outputs are input.
Tool: one persistent `python -I` child per attempt, Jupyter-like (last expression echoed), 60 s per call (killed and restarted empty on a timeout), 8 GB, output cut at 4,000 characters, at most 30 calls and 38,000 generated tokens. Sockets, subprocesses and files under the project's
data / model folders are blocked by an audit hook (the container can reach the internet: found 2026-11-25; audit of 64,753 stored programs: 15 tried the network, none graded right). Word problems run in the corrected environment (cp_model.INT_MAX).
usage: POC_BASE_URL=... python tir_native.py run <set> <effort> <seed>   sets: comp euler eulert mconf oeisf oeis  and any run_nlopt set   -> results/x44/tir_<set>_<effort>_s<seed>.jsonl"""
import json, os, re, subprocess, sys, threading, zlib, tempfile, resource, select, time
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE); R = f"{ROOT}/results/x44"
CALL, RET = 200012, 200002
CAP, MAXCALLS, TOOL_S, OUTC = 38000, 30, 60, 4000
SYS = ("<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2024-06\nCurrent date: 2026-11-25\n\nReasoning: {e}\n\n# Tools\n\n## python\n\n"
       "Use this tool to execute Python code in your chain of thought. The code will not be shown to the user. This tool should be used for internal reasoning, not for code that is intended to be visible to the user "
       "(e.g. when creating plots, tables, or files).\n\nWhen you send a message containing Python code to python, it will be executed in a stateful Jupyter notebook environment. python will respond with the output of the execution or "
       "time out after 60.0 seconds. Internet access for this session is disabled.\n\n# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|>"
       "<|start|>user<|message|>{q}<|end|><|start|>assistant")
DRIVER = r'''
import sys, os, io, json, ast, traceback
_real = os.fdopen(os.dup(1), "w"); _in = os.fdopen(os.dup(0)); sys.stdin = io.StringIO("")
def _hook(ev, args):
    if ev in ("socket.connect", "socket.getaddrinfo", "socket.bind", "socket.gethostbyname", "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.fork", "os.forkpty", "pty.spawn"):
        raise PermissionError("blocked in this session: " + ev)
    if ev in ("open", "os.listdir", "os.scandir", "glob.glob", "os.chdir") and args and isinstance(args[0], (str, bytes)):
        p = args[0].decode("utf8", "ignore") if isinstance(args[0], bytes) else args[0]
        p = os.path.realpath(p)
        if p.startswith(("/NAS", "/SSD", "/dev/shm")) and "site-packages" not in p:
            raise PermissionError("blocked in this session: " + ev)
try:
    from ortools.sat.python import cp_model as _cm
    _cm.INT_MAX = 2 ** 31 - 1; _cm.INT_MIN = -(2 ** 31 - 1)
except Exception:
    pass
import numpy, sympy, scipy, multiprocessing
G = {"__name__": "__main__"}
sys.addaudithook(_hook)
for line in _in:
    code = json.loads(line); buf = io.StringIO(); o, e = sys.stdout, sys.stderr; sys.stdout = sys.stderr = buf
    try:
        t = ast.parse(code); last = t.body.pop() if t.body and isinstance(t.body[-1], ast.Expr) else None
        exec(compile(t, "<cell>", "exec"), G)
        if last is not None:
            v = eval(compile(ast.Expression(last.value), "<cell>", "eval"), G)
            if v is not None:
                print(repr(v))
    except BaseException:
        traceback.print_exc(limit=-3)
    sys.stdout, sys.stderr = o, e
    _real.write(json.dumps(buf.getvalue()[-200000:]) + "\n"); _real.flush()
'''
SEM = threading.Semaphore(int(os.environ.get("TIR_PAR", 16)))


def _lim():
    os.setsid(); resource.setrlimit(resource.RLIMIT_AS, (8 << 30, 8 << 30)); resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))


class Tool:
    def __init__(self):
        self.p = None; self.d = tempfile.TemporaryDirectory(prefix="sbx_tir_"); self.f = os.path.join(self.d.name, "driver.py"); open(self.f, "w").write(DRIVER)

    def start(self):
        self.p = subprocess.Popen([sys.executable, "-I", self.f], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=self.d.name, preexec_fn=_lim,
                                  env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "MALLOC_ARENA_MAX": "2", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        self.buf = b""

    def kill(self):
        if self.p:
            try:
                os.killpg(self.p.pid, 9)
            except ProcessLookupError:
                pass
            self.p.wait(); self.p.stdin.close(); self.p.stdout.close(); self.p = None

    def run(self, code):
        with SEM:
            try:
                if self.p is None or self.p.poll() is not None:
                    self.kill(); self.start(); self.call("0", 120)   # imports (sympy, ortools) are not charged to the first cell's 60 s
                return self.call(code, TOOL_S)
            except TimeoutError:
                self.kill(); return f"Execution timed out after {TOOL_S}.0 seconds. The session was restarted; variables are lost."
            except (BrokenPipeError, EOFError, OSError):
                self.kill(); return "The session died (memory limit or crash) and was restarted; variables are lost."

    def call(self, code, t):
        self.p.stdin.write((json.dumps(code) + "\n").encode()); self.p.stdin.flush(); end = time.time() + t
        while b"\n" not in self.buf:
            r, _, _ = select.select([self.p.stdout], [], [], max(0, end - time.time()))
            if not r:
                raise TimeoutError
            c = os.read(self.p.stdout.fileno(), 1 << 16)
            if not c:
                raise EOFError
            self.buf += c
        l, self.buf = self.buf.split(b"\n", 1)
        o = json.loads(l)
        return o if len(o) <= OUTC else o[:OUTC // 2] + "\n[... output cut ...]\n" + o[-OUTC // 2:]

    def close(self):
        self.kill(); self.d.cleanup()


def solve(q, effort, seed):
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    ids = tok(SYS.format(e=effort, q=q)); used = calls = 0; T = Tool(); codes = []; outs = []; fin = "stop"; text = ""; lastout = ""; tooltok = prefill = 0
    try:
        while True:
            room = min(CAP - used, int(os.environ.get("TIR_CTX", 64000)) - len(ids) - 8)
            if room < 16:
                fin = "length"; break
            r = llm.client.completions.create(model="local", prompt=ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=seed + calls,
                                              extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [CALL, RET]})
            prefill += len(ids); c = r.choices[0]; g = list(c.token_ids); used += r.usage.completion_tokens; text = c.text or ""; fin = c.finish_reason
            if fin == "length":
                break
            if CALL in (g[-1] if g else None, c.stop_reason):
                if g[-1] != CALL:
                    g.append(CALL)
                m = text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]
                calls += 1
                if calls > MAXCALLS:
                    fin = "calls"; break
                o = T.run(code) if "python" in head else "Unknown tool. Only python is available."
                codes.append(code); lastout = o; outs.append(o[:300])
                oi = tok(o); tooltok += len(oi); ids = ids + g + tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + oi + tok("<|end|><|start|>assistant")
                continue
            break
    finally:
        T.close()
    final = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "codes": codes, "outs": outs, "tool_tokens": tooltok, "prefill_tokens": prefill}


def task(st):
    """-> (problems, prompt(p), grade(p, final) -> dict)"""
    if st == "comp":
        import ma_effort as M
        return M.PROBS, lambda p: M.PROMPT.format(p=p["problem"]), lambda p, t: (lambda a: {"pred": a, "correct": a is not None and a == p["gold"].strip()})(M.ans(t))
    if st in ("euler", "eulert", "mconf", "oeis", "oeisf"):
        import run_compute as RC
        P = RC.problems(st)
        if st.startswith("euler"):
            return P, lambda p: RC.EULER_THINK.replace(" You may not run code.", "").format(p=p["problem"]), lambda p, t: (lambda a: {"pred": a, "correct": bool(a) and RC.norm(a) == RC.norm(p["answer"])})(RC.boxed(t))
        if st == "mconf":
            def gm(p, t):
                try:
                    _, ok, d = RC._MC[p["id"]].parse_and_check([{"role": "assistant", "content": t}]) if t else (None, False, "no answer")
                except Exception as e:
                    ok, d = False, f"grader error {type(e).__name__}"
                return {"pred": t[-600:], "correct": bool(ok), "detail": str(d)[:200]}
            return P, lambda p: p["problem"], gm
        def go(p, t):
            from llm import last_block
            code = last_block(t, ("python", "py", "python3", ""))
            ok, right, outs = RC.run_seq(code, p["offset"], p["terms"]) if code else (False, 0, [])
            return {"pred": outs[:20], "outs_": outs, "code": code, "correct": ok, "right": right}
        return P, lambda p: RC.OEIS.format(name=p["name"], comments=p["comments"]), go
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    import run_compute as RC
    def gw(p, t):
        a = RC.boxed(t); v = None
        if a:
            s = re.sub(r"\\text\{|\\[,;! ]|\\\$|\\%|[$,{}]", "", a)
            v = "NBS" if re.search(r"no\s*best\s*solution|infeasible", a, re.I) else RN.value_of((re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", s) or [""])[-1])
        return {"pred": v, "correct": RN.correct(v, p["gold"]) if v is not None else False}
    LIB = ("\n\nFormulate this problem and solve it to proven optimality with a suitable solver library in the python tool: Google OR-Tools (`pywraplp` with SCIP for linear / mixed-integer models, CP-SAT), cvxpy (convex continuous models, including quadratic and "
           "second-order cone constraints) or scipy.optimize. Put the optimal objective value alone in \\boxed{}; if the problem has no feasible solution, put \\boxed{No Best Solution}.")
    return RN.problems(st), lambda p: p["q"] + LIB, gw


def main(st, effort, seed):
    P, prompt, grade = task(st); path = f"{R}/tir_{st}_{effort}_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        for k in range(2):
            try:
                z = solve(prompt(p), effort, seed * 1000 + zlib.crc32(p["id"].encode()) % 997); break
            except Exception as e:
                z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "codes": [], "outs": []}
        z.update(id=p["id"], **grade(p, z["final"])); z["final"] = z["final"][-1500:]; z["codes"] = [c[:3000] for c in z["codes"]]
        return z
    N = int(os.environ.get("TIR_N", 0)) or len(P)
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 32))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P[:N] if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]; n = len(Z)
    print(f"TIR {st} {effort} s{seed}: {100*sum(z['correct'] for z in Z)/n:.1f}% of {n} @ {sum(z['out_tokens'] for z in Z)/n/1000:.2f}k; calls {sum(z['calls'] for z in Z)/n:.1f}; finish {({k: sum(z['finish'] == k for z in Z) for k in set(z['finish'][:8] if z['finish'].startswith('error') else z['finish'] for z in Z)})}; "
          f"no final {sum(not z['final'] for z in Z)}; zero-token {sum(z['out_tokens'] == 0 for z in Z)}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "tooltest":
        T = Tool()
        for c in ("x=3\nx*7", "print(x)", "import urllib.request as u\nu.urlopen('https://oeis.org',timeout=3)", "open('/NAS/SJ/POSTECH/nlp_data/compute/oeis.json').read()[:20]", "import subprocess\nsubprocess.run(['ls'])", "import os\nos.listdir('/NAS')",
                  "import time\ntime.sleep(70)", "x", "from ortools.sat.python import cp_model as cm\nm=cm.CpModel();a=m.NewIntVar(0,cm.INT_MAX,'a');m.Add(a<=5);m.Maximize(a);s=cm.CpSolver();s.Solve(m);s.ObjectiveValue()",
                  "from sympy import *\nfactorint(2**67-1)", "import cvxpy as cp\nx=cp.Variable();p=cp.Problem(cp.Minimize((x-2)**2));p.solve()", "from ortools.linear_solver import pywraplp\ns=pywraplp.Solver.CreateSolver('SCIP');v=s.IntVar(0,9,'v');s.Maximize(v);s.Solve();s.Objective().Value()", "b=bytearray(20<<30)", "1+1"):
            print(">>", c[:60].replace("\n", " | "), "->", T.run(c)[-220:].strip().replace("\n", " | "), flush=True)
        T.close()
    else:
        main(sys.argv[2], sys.argv[3], int(sys.argv[4]))
