"""RFT-C rollouts and evaluation (PREREG_DIFF, 2026-11-26). The OWN-E recipe of MathConstruct (native tool, installed-solver sentence, submit(s) with
the solver's own check; tir_submit's harness and texts, unchanged) with the token ids of every attempt recorded, so right attempts can be used as
supervised traces: `ids` is the whole conversation, `mask` is 1 on tokens the model generated and 0 on the prompt, tool outputs and user notes.
Sets: train (instances_rft.jsonl, training problems only), held (mcong instances of the held-out problems), trainp (mcong instances of the training problems).
usage: TIR_ENV=1 POC_BASE_URL=... python rft_gen.py <tag> <set> <seed> [k]   -> results/x44/rft_<tag>_<set>_s<seed>.jsonl  (k samples per instance, seeds seed..seed+k-1)
Temporary files: each attempt's sandbox is removed by Tool.close()."""
import ast, json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
assert os.environ.get("TIR_ENV"), "RFT-C uses the OWN-E recipe: set TIR_ENV=1"
import tir_native as T
import tir_submit as TS
import run_compute as RC
R = T.R; BASE = os.path.join(os.path.dirname(RC.DATA), "construct")


def problems(st):
    RC.mcong_problems()                                       # fills RC._MC for mcong and loads the package
    from math_construct.problems import get_all_problem_classes
    C = {c.config.name: c for c in get_all_problem_classes()}; sp = json.load(open(f"{BASE}/rft_split.json"))
    src = f"{BASE}/instances_rft.jsonl" if st == "train" else f"{BASE}/instances_g.jsonl"; keep = set(sp["heldout"] if st == "held" else sp["train"])
    out = []
    for l in open(src):
        x = json.loads(l)
        if x["name"] not in keep:
            continue
        try:
            obj = C[x["name"]](**(x["params"] if isinstance(x["params"], dict) else ast.literal_eval(x["params"])))
        except Exception:
            continue
        RC._MC[x["id"]] = obj; out.append({"id": x["id"], "problem": str(obj) + "\n\nFormat your reply as follows:\n" + obj.get_formatting()})
    return out


def grade(p, t):
    try:
        _, ok, d = RC._MC[p["id"]].parse_and_check([{"role": "assistant", "content": t}]) if t else (None, False, "no answer")
    except Exception as e:
        ok, d = False, f"grader error {type(e).__name__}"
    return {"correct": bool(ok), "detail": str(d)[:200]}


def solve(q, effort, seed):
    """tir_submit.solve (arm OWN) with ids and the generated-token mask recorded"""
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    q = q + TS.TAIL + TS.OWN
    ids = tok(T.SYS.format(e=effort, q=q)); mask = [0] * len(ids); used = calls = 0; tool = T.Tool(); open(tool.f, "w").write(TS.T_DRIVER); subs = []; msgs = 0; fin = "stop"; text = ""; final = ""
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
            if subs and any(x["final"] for x in subs):
                final = "\\boxed{" + next(x for x in subs if x["final"])["s"] + "}"; fin = "submitted"; break
            add(tok("<|start|>python to=assistant<|channel|>analysis<|message|>") + tok(o) + tok("<|end|><|start|>assistant"), 0)
    finally:
        tool.close()
    if not final:
        final = text.split("<|channel|>final<|message|>")[-1].split("<|return|>")[0] if "<|channel|>final<|message|>" in text else ""
        if "\\boxed" not in final and subs:
            final = "\\boxed{" + subs[-1]["s"] + "}"
    return {"final": final, "out_tokens": used, "calls": calls, "finish": fin, "ids": ids, "mask": mask}


def main(tag, st, seed, k):
    P = problems(st); eff = os.environ.get("POC_REASONING_EFFORT", "medium"); path = f"{R}/rft_{tag}_{st}_s{seed}.jsonl"
    done = {(json.loads(l)["id"], json.loads(l)["seed"]) for l in open(path)} if os.path.exists(path) else set()
    jobs = [(p, s) for p in P for s in range(seed, seed + k) if (p["id"], s) not in done]

    def one(ps):
        p, s = ps
        try:
            z = solve(p["problem"], eff, s * 1000 + zlib.crc32(p["id"].encode()) % 997)
        except Exception as e:
            z = {"final": "", "out_tokens": 0, "calls": 0, "finish": "error " + repr(e)[:200], "ids": [], "mask": []}
        z.update(id=p["id"], seed=s, **grade(p, z["final"])); z["final"] = z["final"][-3000:]
        if not (st == "train" and z["correct"]):
            z.pop("ids"); z.pop("mask")                    # traces are kept only for right training attempts
        return z
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, j) for j in jobs]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    Z = [json.loads(l) for l in open(path)]; n = len(Z)
    print(f"RFT-C {tag} {st} s{seed}+{k}: {100*sum(z['correct'] for z in Z)/n:.1f}% of {n} attempts @ {sum(z['out_tokens'] for z in Z)/n/1000:.2f}k; instances with a right attempt "
          f"{len({z['id'] for z in Z if z['correct']})} of {len({z['id'] for z in Z})}; finish {dict((x, sum(z['finish'] == x for z in Z)) for x in {z['finish'][:9] for z in Z})}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
