"""MT secondary (docs/prereg/PREREG_MT.md, addendum "input tokens"): in an agent loop every step re-reads the conversation, so the
arms differ in input tokens as well as output tokens (a 20-step loop re-reads the context 20 times). The rows keep the calls, not the
prompts, so each trajectory is replayed: its calls run again in BFCL's environment classes (deterministic; the replayed results are
checked against the stored 200-character prefixes) and every step's prompt is counted with the Qwen3 chat template and tokenizer
(the same unit for every model; Qwen3.5-9B's own tokenizer is not on the login node). Per step k: prompt P_k (system, every user
message, every earlier answer and tool result, the generation prompt); new_k = P_k - P_(k-1) (P_0 for the first step), the part a
prefix cache over the previous request does not hold. Answers: non-thinking steps count their output tokens minus the stop token
(exact); thinking steps count the answer as replayed (calls re-serialized; a final text answer from its stored first 300 characters:
an undercount for long final answers of thinking steps). A request refused for overflow counts nothing.
  replay (grader venv):  /home1/leesangjun/venvs/bfcl/bin/python poc/mt_cost.py replay <tag> [arms NTEF] [seeds 1 2 3]
                         -> results/tc/mt_in_<tag>_<arm>_s<seed>.json {id: {in, new, mis}}
  report:                python3.11 poc/mt_cost.py report [tag ...]
Utility with input priced (points): 100 x right - 0.5 x (output + rho x new + rho_c x (in - new)) / 1000, rho = 0.25 (input at a
quarter of the output price), rho_c = rho / 10 (a cached input token at a tenth of an input token); also rho_c = rho (no cache) and
rho = 0.1 / 0.5."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
DATA = os.environ.get("MT_ITEMS") or os.path.join(PD, "bfcl", "mt_items.jsonl")
TOK = os.path.join(PD, "stage", "Qwen3-14B-AWQ")


def replay(tag, arms, seeds):
    import bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils as U
    from transformers import AutoTokenizer
    tk = AutoTokenizer.from_pretrained(TOK)
    n = lambda s: len(tk(s, add_special_tokens=False)["input_ids"])
    GEN = {False: n("<|im_start|>assistant\n<think>\n\n</think>\n\n"), True: n("<|im_start|>assistant\n")}
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    sysn = {}
    for a in arms:
        for s in seeds:
            f = f"{RES}/mt_{tag}_{a}_s{s}.jsonl"
            if not os.path.exists(f):
                continue
            out, name = {}, f"cost_{tag}_{a}_s{s}"
            for r in map(json.loads, open(f)):
                p = P[r["id"]]; cfg, cls = p["initial_config"], p["involved_classes"]
                U.execute_multi_turn_func_call([], cfg, cls, name, p["id"], long_context=False)
                if p["id"] not in sysn:
                    sysn[p["id"]] = n(f"<|im_start|>system\n{p['system']}<|im_end|>\n")
                L, prev, tin, tnew, mis = sysn[p["id"]], 0, 0, 0, 0
                for ti, t in enumerate(r["turns"]):
                    L += sum(n(f"<|im_start|>user\n{m['content']}<|im_end|>\n") for m in p["turns"][ti])
                    for st in t:
                        if st.get("fin") == "overflow":
                            continue
                        pk = L + GEN[st["think"]]
                        tin += pk; tnew += pk - prev if prev else pk; prev = pk
                        if st["calls"]:
                            ans = n("[" + ", ".join(st["calls"]) + "]")
                        else:
                            ans = n(st.get("text", ""))
                        if not st["think"]:
                            ans = max(ans, st["tok"] - 1)   # the exact answer length (a call answer may carry prose)
                        L += 5 + ans   # <|im_start|>assistant\n ... <|im_end|>\n
                        if st["calls"]:
                            res, _ = U.execute_multi_turn_func_call(st["calls"], cfg, cls, name, p["id"], long_context=False)
                            mis += sum(x[:200] != y for x, y in zip(res, st["res"]))
                            L += n("<|im_start|>user\n" + "\n".join(f"<tool_response>\n{x}\n</tool_response>" for x in res) + "<|im_end|>\n")
                for c in cls:
                    U.__dict__.pop(re.sub(r"[-./:]", "_", f"{name}_{p['id']}_{c}_instance"), None)
                out[r["id"]] = {"in": tin, "new": tnew, "mis": mis}
            json.dump(out, open(f"{RES}/mt_in_{tag}_{a}_s{s}.json", "w"))
            k = max(1, len(out))
            print(f"{tag} {a} s{s}: {len(out)} rows; input {sum(v['in'] for v in out.values()) / k / 1000:.1f}k per item, new "
                  f"{sum(v['new'] for v in out.values()) / k / 1000:.1f}k; replay mismatches {sum(v['mis'] for v in out.values())}", flush=True)


def report(tags):
    from analyze_mt import ARMS, SEEDS, load
    from analyze_ho3 import ci
    V = {k: [] for k in ("S1", "S2", "S3", "S4")}
    for tag in tags:
        D = {}
        for a in ARMS:
            for s in SEEDS:
                g, f = load(tag, a, s), f"{RES}/mt_in_{tag}_{a}_s{s}.json"
                if g is None or not os.path.exists(f):
                    D = None; break
                I = json.load(open(f)); D[(a, s)] = {i: dict(r, **I[i]) for i, r in g.items() if i in I}
            if D is None:
                break
        if D is None:
            print(f"=== {tag}: missing rows, grades or replays"); continue
        ids = sorted(set.intersection(*(set(v) for v in D.values())))
        mean = lambda a, i, f: sum(f(D[(a, s)][i]) for s in SEEDS) / len(SEEDS)

        def U(rho, rc):
            return lambda r: float(r["ok"]) - 0.5 / 100 * (r["tok"] + rho * r["new"] + rc * (r["in"] - r["new"])) / 1000
        print(f"=== {tag}: {len(ids)} items x {len(SEEDS)} seeds")
        for a in ARMS:
            print(f"  {a}: right {100 * sum(mean(a, i, lambda r: r['ok']) for i in ids) / len(ids):.1f}%; per item output "
                  f"{sum(mean(a, i, lambda r: r['tok']) for i in ids) / len(ids) / 1000:.2f}k, input "
                  f"{sum(mean(a, i, lambda r: r['in']) for i in ids) / len(ids) / 1000:.1f}k (new "
                  f"{sum(mean(a, i, lambda r: r['new']) for i in ids) / len(ids) / 1000:.1f}k)")
        for k, x, y, f in (("S1 T - N input", "T", "N", lambda r: r["in"]), ("S2 T - N input + output", "T", "N", lambda r: r["in"] + r["tok"]),
                           ("S3 E - T input", "E", "T", lambda r: r["in"])):
            g = ci({i: (mean(x, i, f) - mean(y, i, f)) / 1e5 for i in ids})
            print(f"  MT-{k} tokens per item: {g[0]:+.1f}k [{g[1]:+.1f}, {g[2]:+.1f}]")
            V[k[:2]].append((tag, g[2] < 0 if k[:2] in ("S1", "S2") else g[1] > 0))
        same = []
        for k, x, y in (("P2", "E", "T"), ("P3", "E", "N"), ("P4", "F", "E")):
            lo = [ci({i: mean(x, i, u) - mean(y, i, u) for i in ids})[1] > 0 for u in (U(0, 0), U(.25, .025))]
            same.append(lo[0] == lo[1])
            print(f"  MT-{k} verdict (lower bound > 0), output only / input priced with a cache: {lo[0]} / {lo[1]}")
        V["S4"].append((tag, all(same)))
        for nm, rho, rc in (("rho .25 cached", .25, .025), ("rho .25 no cache", .25, .25), ("rho .1 cached", .1, .01),
                            ("rho .5 cached", .5, .05)):
            u = U(rho, rc)
            line = " | ".join(f"{a} {100 * sum(mean(a, i, u) for i in ids) / len(ids):.1f}" for a in ARMS)
            tests = [("E-T", "E", "T"), ("E-N", "E", "N"), ("F-E", "F", "E"), ("T-N", "T", "N")]
            g = {k: ci({i: mean(x, i, u) - mean(y, i, u) for i in ids}) for k, x, y in tests}
            print(f"  utility, {nm}: {line}; " + "; ".join(f"{k} {v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]" for k, v in g.items()))
    print("*** " + "; ".join(f"MT-{k} {sum(x[1] for x in v)} / {len(v)} ({', '.join(t for t, ok in v if ok) or '-'})" for k, v in V.items()))


if __name__ == "__main__":
    if sys.argv[1] == "replay":
        sys.path.insert(0, os.path.join(PD, "bfcl", "pkg"))
        replay(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "NTEF", [int(x) for x in sys.argv[4:]] or [1, 2, 3])
    else:
        report(sys.argv[2:] or ["q14a", "q35", "q8b"])
