"""SUBMIT-F (PREREG_DIFF, 2026-11-27): OWN-E with the benchmark's own answer-format parser at submit. 10% of OWN-E attempts on mcong end
"unparseable" (LaTeX arrays, wrong brackets, an empty box); the parser (Problem.parse: last box, primitive type, list depth of the format — no answer
values, no check) is run on each submission outside the sandbox, and a parse failure returns only the parser's message to the session, at most
FMT_TRIES times; a parseable submission ends the attempt as before. Same seeds as the stored OWN-E rows, so trajectories match up to the first
unparseable submission. usage: TIR_ENV=1 POC_BASE_URL=... python tir_submit_fmt.py <seed> -> results/x44/tirsubf_OWN_mcong_medium_s<seed>.jsonl"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
assert os.environ.get("TIR_ENV"), "OWN-E: set TIR_ENV=1"
import tir_native as T
import tir_submit as TS
import run_compute as RC
R = T.R; FMT_TRIES = int(os.environ.get("FMT_TRIES", 2))


def fmt_error(prob, text):
    try:
        r = prob.parse(text)
        return None if r is not None else "the parser returned nothing"
    except Exception as e:
        return str(e)


def solve(q, effort, seed, prob):
    """rft_gen.solve (tir_submit arm OWN, unchanged up to the first submission) + the official-format parse check at submit"""
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    q = q + TS.TAIL + TS.OWN
    ids = tok(T.SYS.format(e=effort, q=q)); mask = [0] * len(ids); used = calls = 0; seen_subs = 0; fmt_log = []; tool = T.Tool(); open(tool.f, "w").write(TS.T_DRIVER); subs = []; msgs = 0; fin = "stop"; text = ""; final = ""
    subf = os.path.join(tool.d.name, "subs.jsonl"); pre = TS.PRE.format(code=repr(""), code2=repr(""), enf=False, sub=repr(subf)); inited = None
    add = lambda xs, m: (ids.extend(xs), mask.extend([m] * len(xs)))
    try:
        while True:
            room = min(T.CAP - used, int(os.environ.get("TIR_CTX", 64000)) - len(ids) - 8)
            if room < 16:
                fin = "length"; break
            r = llm.client.completions.create(model=os.environ.get("RFT_MODEL", "local"), prompt=ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=seed + calls, extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            c = r.choices[0]; g = list(c.token_ids); used += r.usage.completion_tokens; text = c.text or ""; fin = c.finish_reason
            if fin == "length":
                break
            if T.CALL not in (g[-1] if g else None, c.stop_reason):
                msgs += 1
                if msgs > 3:
                    add(g, 1); break
                base = g[:-1] if g and g[-1] == T.RET else g
                add(base, 1); add(tok("<|end|><|start|>user<|message|>Your answer was not submitted. Call submit(s) in the python tool with the text that goes inside the box, built by your code from a value it computed.<|end|><|start|>assistant"), 0); continue
            if g[-1] != T.CALL:
                g.append(T.CALL)
            m = text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]; calls += 1
            if calls > 200:
                fin = "calls"; break
            if tool.p is None or tool.p is not inited or tool.p.poll() is not None:
                tool.run(pre); inited = tool.p
            o = tool.run(code) if "python" in head else "Unknown tool. Only python is available."
            add(g, 1)
            subs = [json.loads(l) for l in open(subf)] if os.path.exists(subf) else []
            newf = [x for x in subs[seen_subs:] if x["final"]]
            if newf:
                cand = "\\boxed{" + newf[0]["s"] + "}"; seen_subs = len(subs); err = fmt_error(prob, cand)
                fmt_log.append({"s": newf[0]["s"][:300], "error": err})
                if err is None or len(fmt_log) > FMT_TRIES:
                    final = cand; fin = "submitted"; break
                tool.run("_S['done'] = False")          # let the session submit again (hidden from the model)
                o = ("FORMAT ERROR: the official answer parser could not read this submission (" + err[:300] + "). This says nothing about whether the object is correct. "
                     "Rebuild s in exactly the required format and call submit(s) again.")
            add(tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + tok(o) + tok("<|end|><|start|>assistant"), 0)
    finally:
        tool.close()
    if not final:
        final = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
        if "\\boxed" not in final and subs:
            final = "\\boxed{" + subs[-1]["s"] + "}"
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "fmt": fmt_log}




def main(seed):
    P, prompt, grade = T.task("mcong"); path = f"{R}/tirsubf_OWN_mcong_medium_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            z = solve(prompt(p), "medium", seed * 1000 + zlib.crc32(p["id"].encode()) % 997, RC._MC[p["id"]])
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "fmt": []}
        z.update(id=p["id"], **grade(p, z["final"])); z["final"] = z["final"][-3000:]; return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"SUBMIT-F s{seed}: {100*sum(z['correct'] for z in Z)/len(Z):.1f}% of {len(Z)} @ {sum(z['out_tokens'] for z in Z)/len(Z)/1000:.2f}k; format feedback used in {sum(bool(z['fmt']) and z['fmt'][0]['error'] is not None for z in Z)}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
