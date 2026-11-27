"""MathConstruct confidence baseline (PREREG_DIFF CONF-MC, 2026-11-27): gpt-oss-120b OWN-E (tir_submit's harness via rft_gen.solve, unchanged) with
top-5 log-probabilities recorded, so DeepConf-style selection (2508.15260) between two attempts and the AUROC of confidence for right vs wrong
constructions can be measured on the current MathConstruct recipe. usage: TIR_ENV=1 POC_BASE_URL=... python tir_submit_lp.py <seed>  -> results/x44/tirsublp_OWN_mcong_medium_s<seed>.jsonl
Temporary files: sandboxes removed by Tool.close()."""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
assert os.environ.get("TIR_ENV"), "OWN-E: set TIR_ENV=1"
import tir_native as T
import tir_submit as TS
R = T.R


def solve(q, effort, seed):
    """rft_gen.solve (tir_submit arm OWN) with top-5 log-probabilities of every generated token summarised (DeepConf confidences)"""
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    q = q + TS.TAIL + TS.OWN
    ids = tok(T.SYS.format(e=effort, q=q)); mask = [0] * len(ids); lps, conf = [], []; used = calls = 0; tool = T.Tool(); open(tool.f, "w").write(TS.T_DRIVER); subs = []; msgs = 0; fin = "stop"; text = ""; final = ""
    subf = os.path.join(tool.d.name, "subs.jsonl"); pre = TS.PRE.format(code=repr(""), code2=repr(""), enf=False, sub=repr(subf)); inited = None
    add = lambda xs, m: (ids.extend(xs), mask.extend([m] * len(xs)))
    try:
        while True:
            room = min(T.CAP - used, int(os.environ.get("TIR_CTX", 64000)) - len(ids) - 8)
            if room < 16:
                fin = "length"; break
            r = llm.client.completions.create(model=os.environ.get("RFT_MODEL", "local"), prompt=ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=seed + calls, logprobs=5, extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            c = r.choices[0]; L = c.logprobs; lps.extend(x for x in ((L.token_logprobs or []) if L else []) if x is not None); conf.extend(-sum(d.values()) / len(d) for d in ((L.top_logprobs or []) if L else []) if d); g = list(c.token_ids); used += r.usage.completion_tokens; text = c.text or ""; fin = c.finish_reason
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
            if subs and any(x["final"] for x in subs):
                final = "\\boxed{" + next(x for x in subs if x["final"])["s"] + "}"; fin = "submitted"; break
            add(tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + tok(o) + tok("<|end|><|start|>assistant"), 0)
    finally:
        tool.close()
    if not final:
        final = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
        if "\\boxed" not in final and subs:
            final = "\\boxed{" + subs[-1]["s"] + "}"
    n = len(conf); W = 1024
    low = min((sum(conf[i:i + W]) / W for i in range(0, n - W + 1, 128)), default=None) if n >= W else (sum(conf) / n if n else None)
    lp = {"n": len(lps), "mean_lp": sum(lps) / len(lps) if lps else None, "mean_conf": sum(conf) / n if n else None, "lowest_group_conf": low, "tail_conf": sum(conf[-2048:]) / len(conf[-2048:]) if n else None}
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "lp": lp}




def main(seed):
    P, prompt, grade = T.task("mcong"); path = f"{R}/tirsublp_OWN_mcong_medium_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        try:
            z = solve(prompt(p), "medium", seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "lp": {}}
        z.update(id=p["id"], **grade(p, z["final"])); z["final"] = z["final"][-3000:]; return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]
    print(f"CONF-MC s{seed}: {100*sum(z['correct'] for z in Z)/len(Z):.1f}% of {len(Z)} @ {sum(z['out_tokens'] for z in Z)/len(Z)/1000:.2f}k", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
