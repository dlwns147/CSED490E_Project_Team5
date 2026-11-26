"""PROV-FB (PREREG_DIFF, 2026-11-26): the provenance flag answered inside the same tool session instead of by a fresh attempt.
One native-tool attempt (tir_native's harness, unchanged); if its final answer was never printed by one of its tool runs, the session is continued once with a user turn that says so, within the same 38k generated-token cap.
The attempt's first final answer is stored too, so ONE (stop at the first answer) and FB (with the feedback turn) are read from the same sample.
usage: POC_BASE_URL=... python tir_provfb.py run <euler|eulert> <effort> <seed> -> results/x44/tirfb_<set>_<effort>_s<seed>.jsonl ; python tir_provfb.py score <seeds...>"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
R = T.R
FB = ("Your final answer {a} does not appear in the output of any of your Python runs, so it was not computed. "
      "Compute it with Python, print it, and then give the final answer in the same format.")


def _final(text):
    return text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""


def solve(q, effort, seed):
    import llm
    import ma_effort as M
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    ids = tok(T.SYS.format(e=effort, q=q)); used = calls = 0; tool = T.Tool(); codes = []; outs = []; fin = "stop"; text = ""; tooltok = prefill = 0
    first = None; fed = False
    try:
        while True:
            room = min(T.CAP - used, int(os.environ.get("TIR_CTX", 64000)) - len(ids) - 8)
            if room < 16:
                fin = "length"; break
            r = llm.client.completions.create(model="local", prompt=ids, temperature=1.0, top_p=0.95, max_tokens=room, seed=seed + calls + (7919 if fed else 0),
                                              extra_body={"return_token_ids": True, "skip_special_tokens": False, "stop_token_ids": [T.CALL, T.RET]})
            prefill += len(ids); c = r.choices[0]; g = list(c.token_ids); used += r.usage.completion_tokens; text = c.text or ""; fin = c.finish_reason
            if fin == "length":
                break
            if T.CALL in (g[-1] if g else None, c.stop_reason):
                if g[-1] != T.CALL:
                    g.append(T.CALL)
                m = text.split("<|call|>")[0].split("<|message|>"); head, code = m[-2].split("<|start|>")[-1] if len(m) > 1 else "", m[-1]
                calls += 1
                if calls > T.MAXCALLS:
                    fin = "calls"; break
                o = tool.run(code) if "python" in head else "Unknown tool. Only python is available."
                codes.append(code); outs.append(o)
                oi = tok(o); tooltok += len(oi); ids = ids + g + tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + oi + tok("<|end|><|start|>assistant")
                continue
            # a final message
            f = _final(text); pv = T.provenance({"final": f, "outs": outs})
            if first is None:
                first = {"final": f, "out_tokens": used, "calls": calls, "prov": pv}
            if fed or pv or not M.ans(f):
                break
            fed = True                                  # one feedback turn, in the same session
            if g and g[-1] == T.RET:
                g = g[:-1]
            ids = ids + g + tok("<|end|><|start|>user<|message|>" + FB.format(a=M.ans(f)) + "<|end|><|start|>assistant")
    finally:
        tool.close()
    final = _final(text) if fin == "stop" else ""
    if first is None:
        first = {"final": "", "out_tokens": used, "calls": calls, "prov": None}
    if fed and not final:                               # the feedback turn ran out: the first answer stands
        final = first["final"]
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "fed": fed, "first": first, "codes": codes, "outs": outs, "tool_tokens": tooltok, "prefill_tokens": prefill}


def main(st, effort, seed):
    P, prompt, grade = T.task(st); path = f"{R}/tirfb_{st}_{effort}_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(p):
        for k in range(2):
            try:
                z = solve(prompt(p), effort, seed * 1000 + zlib.crc32(p["id"].encode()) % 997); break
            except Exception as e:
                z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "fed": False, "first": {"final": "", "out_tokens": 0, "calls": 0, "prov": None}, "codes": [], "outs": []}
        z.update(id=p["id"], **grade(p, z["final"])); z["first"].update(**{"first_" + k: v for k, v in grade(p, z["first"]["final"]).items()})
        z["final"] = z["final"][-4000:]; z["first"]["final"] = z["first"]["final"][-4000:]; z["codes"] = [c[:3000] for c in z["codes"]]; z["outs"] = [o[:300] for o in z["outs"]]
        return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 32))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]; n = len(Z)
    print(f"PROV-FB {st} {effort} s{seed}: first {100*sum(bool(z['first']['first_correct']) for z in Z)/n:.1f}% @ {sum(z['first']['out_tokens'] for z in Z)/n/1000:.2f}k -> final {100*sum(bool(z['correct']) for z in Z)/n:.1f}% @ {sum(z['out_tokens'] for z in Z)/n/1000:.2f}k; "
          f"fed {sum(z['fed'] for z in Z)}; finish {({k: sum(z['finish'] == k for z in Z) for k in set(z['finish'][:8] for z in Z)})}; zero-token {sum(z['out_tokens'] == 0 for z in Z)}", flush=True)


def score(seeds):
    import tir_score as S
    U = S.U; A = {"ONE": {}, "FB": {}}
    for st in ("euler", "eulert"):
        for s in seeds:
            for r in map(json.loads, open(f"{R}/tirfb_{st}_medium_s{s}.jsonl")):
                k = (st, r["id"])
                A["ONE"].setdefault(k, []).append((float(bool(r["first"]["first_correct"])), r["first"]["out_tokens"]))
                A["FB"].setdefault(k, []).append((float(bool(r["correct"])), r["out_tokens"]))
    A = {a: {k: (sum(x for x, _ in v) / len(v), sum(t for _, t in v) / len(v)) for k, v in d.items()} for a, d in A.items()}
    for lab, sts in (("euler", ("euler",)), ("eulert", ("eulert",)), ("pooled", ("euler", "eulert"))):
        ks = [k for k in A["FB"] if k[0] in sts]
        for a in A:
            print(f"{lab:7s} {a:4s} n={len(ks)} {100*sum(A[a][k][0] for k in ks)/len(ks):.1f}% @ {sum(A[a][k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*A[a][k]) for k in ks)/len(ks):.2f}")
        print(f"{lab:7s} FB − ONE: accuracy {S.ci([100*(A['FB'][k][0]-A['ONE'][k][0]) for k in ks])} ktok {S.ci([(A['FB'][k][1]-A['ONE'][k][1])/1000 for k in ks])} utility {S.ci([U(*A['FB'][k])-U(*A['ONE'][k]) for k in ks])}")


if __name__ == "__main__":
    if sys.argv[1] == "score":
        score([int(x) for x in sys.argv[2:]])
    else:
        main(sys.argv[2], sys.argv[3], int(sys.argv[4]))
