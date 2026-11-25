"""PREREG_DIFF addendum SUBMIT (2026-11-25): the answer of a native-tool attempt is a value of the session. The attempt ends at submit(s) inside Python (s = the text that goes in the box, built by code); arms:
  S0 no check; OWN the solver is told to write and run its own check first (not enforced); BLIND a check(s) written from the statement alone by a separate call that never sees the solution runs at submit: a rejected submission returns the failed
  conditions into the same session (at most 3 rejections, then the last value stands); a check that crashes or runs over 20 s cannot reject. The blind call's tokens are charged.
usage: POC_BASE_URL=... python tir_submit.py run <S0|OWN|BLIND> <set> <effort> <seed>   (sets: mconf mcon euler eulert)   |  python tir_submit.py selftest"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
R = T.R; PRE = r'''
import signal as _sig, json as _js
_CODE = {code}
_ENF = {enf}
_S = {{"n": 0}}
_NS = {{}}
try:
    exec(_CODE, _NS)
except BaseException:
    _NS = {{}}
def _alarm(*a):
    raise TimeoutError("check over 20 s")
def submit(s):
    import re as _re
    s = str(s).strip(); bad = []; note = ""; _m = _re.fullmatch(r"(?s)\\boxed{{(.*)}}", s); s = _m.group(1).strip() if _m else s
    if _ENF and callable(_NS.get("check")):
        old = _sig.signal(_sig.SIGALRM, _alarm); _sig.setitimer(_sig.ITIMER_REAL, 20)
        try:
            errs, res = [], []
            for form in (s, chr(92) + "boxed{{" + s + "}}"):          # the check may expect the box or its content: it rejects only if every form it can read is rejected; a crash / parse failure cannot reject
                try:
                    res.append([str(x)[:300] for x in (_NS["check"](form) or [])][:6])
                except TimeoutError:
                    raise
                except BaseException as e:
                    errs.append(type(e).__name__ + ": " + str(e)[:150])
            bad = min(res, key=lambda r: sum("boxed" in x.lower() for x in r)) if res and all(res) else []; note = "check error " + errs[0] if errs and not res else ""
        except BaseException as e:
            bad = []; note = "check error " + type(e).__name__ + ": " + str(e)[:150]
        finally:
            _sig.setitimer(_sig.ITIMER_REAL, 0); _sig.signal(_sig.SIGALRM, old)
    _S["n"] += 1
    fin = (not bad) or _S["n"] > 3
    if not _S.get("done"):
        with open({sub}, "a") as f:
            f.write(_js.dumps({{"s": s, "final": fin, "bad": bad, "note": note, "n": _S["n"]}}) + chr(10))
    _S["done"] = _S.get("done") or fin
    if fin:
        print("submitted")
    if not fin:
        print("REJECTED (%d of 3). These stated conditions fail:" % _S["n"]); [print(" -", b) for b in bad]
'''
TAIL = ("\n\nFinish by calling submit(s) in the python tool (the function already exists in the session). s is the exact text that goes inside \\boxed{...} in the required format, built by your code from the computed value "
        "(plain text, no LaTeX spacing commands). The attempt ends at that call; no further message is needed.")
OWN = " Before that, write a function in the session that tests every condition the problem states on the final object, run it, and submit only if it passes."
BLINDT = " submit runs a check of the stated conditions; if it prints REJECTED, fix the object and submit again."
SPEC = ("Below is a problem that asks for an answer in a fixed format. Do NOT solve it. Write one Python 3 function `check(s)` that tests a proposed answer against the conditions the problem states.\n"
        "- s is a string: the text that stands inside \\boxed{{...}} in the required format, WITHOUT the \\boxed itself. Parse it tolerantly (spaces, LaTeX spacing and fractions / roots, line breaks, (), [], {{}} as list brackets, an array environment if the format uses one). "
        "If you cannot parse s, raise ValueError; never report a format problem as a violated condition.\n"
        "- Return a list of short strings, one per violated condition; return [] if every stated condition holds. Test only conditions the statement gives, with the given parameters; never require a particular answer. If a condition cannot be tested "
        "by computation, skip it.\n- It must run within 10 seconds; standard library, numpy and sympy only; no input, no prints, no files.\n\nProblem:\n{p}\n\nGive the function in a single ```python code block.")


def prompt_spec(p):
    return SPEC.format(p=p)


def solve(q, effort, seed, arm, spec_code):
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    q = q + TAIL + {"S0": "", "OWN": OWN, "BLIND": BLINDT}[arm]
    ids = tok(T.SYS.format(e=effort, q=q)); used = calls = prefill = tooltok = 0; tool = T.Tool(); codes, outs, subs = [], [], []; msgs = 0; fin = "stop"; text = ""; final = ""
    subf = os.path.join(tool.d.name, "subs.jsonl"); pre = PRE.format(code=repr(spec_code or ""), enf=arm == "BLIND", sub=repr(subf)); inited = None
    try:
        while True:
            room = min(T.CAP - used, int(os.environ.get("TIR_CTX", 64000)) - len(ids) - 8)
            if room < 16:
                fin = "length"; break
            prefill += len(ids)
            r = llm.client.completions.create(model="local", prompt=ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=seed + calls, extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            c = r.choices[0]; g = list(c.token_ids); used += r.usage.completion_tokens; text = c.text or ""; fin = c.finish_reason
            if fin == "length":
                break
            if T.CALL not in (g[-1] if g else None, c.stop_reason):
                fm = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
                msgs += 1
                if msgs > 3:
                    break
                note = "Your answer was not submitted. Call submit(s) in the python tool with the text that goes inside the box, built by your code from a value it computed."
                if arm == "BLIND":
                    note += " submit also checks the stated conditions."
                base = g[:-1] if g and g[-1] == T.RET else g
                ids = ids + base + tok("<|end|><|start|>user<|message|>" + note + "<|end|><|start|>assistant"); continue
            if g[-1] != T.CALL:
                g.append(T.CALL)
            m = text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]; calls += 1
            if calls > 200:
                fin = "calls"; break
            if tool.p is None or tool.p is not inited or tool.p.poll() is not None:      # a new session (first call, or after a timeout / crash) gets submit() again
                tool.run(pre); inited = tool.p
            o = tool.run(code) if "python" in head else "Unknown tool. Only python is available."
            codes.append(code); outs.append(o)
            subs = [json.loads(l) for l in open(subf)] if os.path.exists(subf) else []
            if subs and any(x["final"] for x in subs):
                final = "\\boxed{" + next(x for x in subs if x["final"])["s"] + "}"; fin = "submitted"; break
            oi = tok(o); tooltok += len(oi); ids = ids + g + tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + oi + tok("<|end|><|start|>assistant")
    finally:
        tool.close()
    if not final:
        final = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
        if "\\boxed" not in final and subs:
            final = "\\boxed{" + subs[-1]["s"] + "}"
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "codes": codes, "outs": outs, "subs": subs, "unsubmitted_messages": msgs, "tool_tokens": tooltok, "prefill_tokens": prefill}


def main(arm, st, effort, seed):
    from llm import chat, last_block
    import run_compute as RC
    if st == "mcon":
        P = RC.problems("mcon"); _, prompt, grade = T.task("mconf")
        for k in list(RC._MC):      # problems("mcon") fills RC._MC by problem name; task("mconf") adds the fresh instances under other ids
            pass
    else:
        P, prompt, grade = T.task(st)
    path = f"{R}/tirsub2_{arm}_{st}_{effort}_s{seed}.jsonl"; done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
    specp = f"{R}/tirsub2_spec_{st}.jsonl"; SP = {json.loads(l)["id"]: json.loads(l) for l in open(specp)} if os.path.exists(specp) else {}
    if arm == "BLIND":
        def spec(p):
            z = chat(prompt_spec(prompt(p)), think=True, max_tokens=12000, temperature=0.7, effort="low", seed=9000 + zlib.crc32(p["id"].encode()) % 997)
            return {"id": p["id"], "code": last_block(z.get("text") or "", ("python", "py", "python3")) or "", "tok": z.get("out_tokens") or 0}
        with ThreadPoolExecutor(32) as ex, open(specp, "a") as f:
            for z in ex.map(spec, [p for p in P if p["id"] not in SP]):
                SP[z["id"]] = z; f.write(json.dumps(z) + "\n"); f.flush()

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997; sp = SP.get(p["id"], {}) if arm == "BLIND" else {}
        for _ in range(2):
            try:
                z = solve(prompt(p), effort, sd, arm, sp.get("code")); break
            except Exception as e:
                z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "codes": [], "outs": [], "subs": []}
        g = grade(p, z["final"])
        # grade every submission too (false alarms of the check: a rejected submission that is right)
        for x in z["subs"]:
            x["right"] = bool(grade(p, "\\boxed{" + x["s"] + "}")["correct"]); x["s"] = x["s"][:1500]
        z.update(id=p["id"], spec_tokens=sp.get("tok", 0), **g); z["out_tokens_total"] = z["out_tokens"] + z["spec_tokens"]; z["final"] = z["final"][-4000:]; z["codes"] = [c[:3000] for c in z["codes"]]; z["outs"] = [o[:300] for o in z["outs"]]
        return z
    N = int(os.environ.get("TIR_N", 0)) or len(P)
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 32))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P[:N] if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]; n = len(Z); rej = [x for z in Z for x in z["subs"] if x["bad"]]
    print(f"SUBMIT {arm} {st} {effort} s{seed}: {100*sum(z['correct'] for z in Z)/n:.1f}% of {n} @ {sum(z['out_tokens_total'] for z in Z)/n/1000:.2f}k (check {sum(z['spec_tokens'] for z in Z)/n/1000:.2f}k); submitted {sum(z['finish']=='submitted' for z in Z)}; rejections {len(rej)}, of right answers {sum(x['right'] for x in rej)}; "
          f"accepted wrong {sum(bool(z['subs']) and not z['subs'][-1]['bad'] and not z['subs'][-1]['right'] for z in Z)}; check errors {sum(bool(x['note']) for z in Z for x in z['subs'])}; zero-token {sum(z['out_tokens']==0 for z in Z)}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        for enf, code in ((True, "def check(s):\n    v=eval(s)\n    return [] if sum(v)==10 else ['sum is %d, not 10'%sum(v)]"), (True, "def check(s):\n    raise ValueError('x')"), (True, "syntax error("), (False, ""), (True, "def check(s):\n    while True: pass")):
            t = T.Tool(); f = os.path.join(t.d.name, "subs.jsonl"); t.run(PRE.format(code=repr(code), enf=enf, sub=repr(f)))
            for c in ("submit([1,2])", "submit(str([4,6]))", "submit('[1]')\nsubmit('[2]')\nsubmit('[3]')\nsubmit('[4]')"):
                print(repr(code[:30]), c[:30].replace("\n", ";"), "->", t.run(c).replace("\n", " | ")[:400])
            print("   file:", open(f).read()[:600] if os.path.exists(f) else None); t.close()
    else:
        main(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
