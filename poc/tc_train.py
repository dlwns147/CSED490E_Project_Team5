"""TC-RL (docs/prereg/PREREG_TCRL.md): plain RL on Qwen3-8B's non-thinking tool calls — CV-1's C1 loop (poc/cv_train.py: LoRA r 16,
GRPO without std normalisation, 8 samples per request, 64 requests per round, one optimizer step per round, lr 2e-5, no KL, 512-token
cap) on ToolACE requests in BFCL's prompt format ($POC_DATA/toolace/tc_train_items.jsonl, poc/prep_tctrain.py), reward = the calls
right (poc/tc_reward.py: the gold calls as a multiset, or no call where the gold makes none). One vLLM server (base + the current adapter,
reloaded each round) on GPU 0, the trainer on GPU 1 (poc/slurm/tc_lane.sh).
Addendum 2: --bil <file> (poc/prep_tcbil.py) replaces the reward with the cascade's own, c x [passes the check] x P_X(y|i) (right - r_D(i)
+ 0.005 kd(i)): the gradient of the deployed cascade's utility with the peer X and the default fixed; with --plus, right + that
term unscaled (the quick answer's own accuracy plus the cascade's utility, both in accuracy units).
--orm (PREREG_LCM.md addendum SEL-TC): no sampling, no server; cv_train.py's orm verifier on tool calls. Pool: the stored calls of
SEL_TC_POOL on the training requests; per request the distinct passing answers (tc_reward.check, keyed by canon), right by tc_reward.right;
requests with a right and a wrong one. Context = the request, a candidate's text as the answer, then TC_ASK; score s = logit(ACCEPT) -
logit(DE); loss per request = mean over (right, wrong) pairs of log(1 + exp(s_w - s_r)).
usage: /opt/conda/bin/python tc_train.py <out dir> [--questions 6000] [--batch 64] [--group 8] [--lr 2e-5] [--smoke N] [--base DIR]
       [--bil FILE [--plus]]
       /opt/conda/bin/python tc_train.py <out dir> --orm [--batch 16] [--lr 5e-5] [--epochs 2] [--save 25] [--smoke N]"""
import json, math, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cv_train import MAXQ, Policy, arg, post, sample  # noqa: E402
from tc_reward import canon, check, right  # noqa: E402

ITEMS = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "toolace", "tc_train_items.jsonl")


TC_ASK = "Are these function calls (or no call) the right response to the request? Reply ACCEPT or DEFER."
SEL_TC_POOL = [(f"taq8b_cheap_s{s}", "n_text") for s in (1, 2, 3, 4)] + [("taq8b_sb_s1", "text")] + \
    [(f"taq35_cheap_s{s}", "n_text") for s in (1, 2, 3, 4)]


def main_orm(out):
    """addendum SEL-TC: the verifier (see the docstring)"""
    from cv_train import rows_of
    os.makedirs(out, exist_ok=True)
    B, lr, ep, save, smoke = arg("--batch", 16), arg("--lr", 5e-5), arg("--epochs", 2), arg("--save", 25), arg("--smoke", 0)
    D = os.path.dirname(ITEMS)
    keep = set(open(os.environ.get("SEL_IDS", f"{D}/tc_train_ids.txt")).read().split())
    items = {p["id"]: p for p in map(json.loads, open(ITEMS)) if p["id"] in keep}
    R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
    G = {i: {} for i in items}   # id -> canon -> [right, texts]
    for f, fld in SEL_TC_POOL:
        rows = rows_of(f"{R}/{f}.jsonl")
        print(f"pool {f}: {sum(r['id'] in G for r in rows)} rows", flush=True)
        for r in rows:
            p = items.get(r["id"])
            t = (r.get(fld) or "").strip() if p else ""
            if not p or not check(t, p["functions"]):
                continue
            k = canon(t)
            if k is None:
                continue
            g = G[r["id"]].setdefault(k, [right(t, p["gold"], p["functions"]) > 0, []])
            if t not in g[1]:
                g[1].append(t)
    Q = sorted((i, {k: v[1] for k, v in g.items() if v[0]}, {k: v[1] for k, v in g.items() if not v[0]}) for i, g in G.items()
               if any(v[0] for v in g.values()) and not all(v[0] for v in g.values()))
    random.Random(0).shuffle(Q)
    Q = Q[:smoke or len(Q)]
    print(f"orm-tc: {len(Q)} requests with a right and a wrong passing answer (of {len(G)}), {sum(len(r) + len(w) for _, r, w in Q)} "
          f"answers; batch {B}, lr {lr}, epochs {ep}", flush=True)
    pol = Policy(arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B"), lr)
    torch = pol.torch
    log = open(f"{out}/log.jsonl", "a")
    step = 0
    for e in range(ep):
        rng = random.Random(1000 + e)
        order = Q[:]
        rng.shuffle(order)
        for a in range(0, len(order), B):
            t0, st = time.time(), {"loss": 0.0, "pairs_ok": 0.0, "q": 0, "cands": 0}
            batch = order[a:a + B]
            for i, Rr, W in batch:
                p = items[i]
                hs = [(k, True) for k in Rr] + [(k, False) for k in W]
                if len(hs) > 8:   # at most 8 answers: one right, one wrong, the rest drawn
                    rest = hs[1:len(Rr)] + hs[len(Rr) + 1:]
                    hs = [hs[0], hs[len(Rr)]] + rng.sample(rest, 6)
                msgs1 = [{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}]
                ctxs = [pol.ids(msgs1 + [{"role": "assistant", "content": rng.choice((Rr if ok else W)[k])},
                                         {"role": "user", "content": TC_ASK}]) for k, ok in hs]
                lab = [ok for _, ok in hs]
                P = pol.ids(msgs1)
                kv = pol.prefix(P[:-1])
                sc = [0.0] * len(ctxs)
                with torch.no_grad():
                    for sub, x in pol.gate_p(kv, P, ctxs, logit=True):
                        for b, v in zip(sub, x.tolist()):
                            sc[b] = v
                pr = [(r, w) for r in range(len(sc)) if lab[r] for w in range(len(sc)) if not lab[w]]
                g = [0.0] * len(sc)
                for r, w in pr:
                    sg = 1.0 / (1.0 + math.exp(sc[r] - sc[w]))
                    g[w] += sg / len(pr) / len(batch); g[r] -= sg / len(pr) / len(batch)
                    st["loss"] += (math.log1p(math.exp(sc[w] - sc[r])) if sc[w] - sc[r] < 30 else sc[w] - sc[r]) / len(pr)
                    st["pairs_ok"] += ((sc[r] > sc[w]) + 0.5 * (sc[r] == sc[w])) / len(pr)
                for sub, x in pol.gate_p(kv, P, ctxs, logit=True):
                    (torch.tensor([g[b] for b in sub], device="cuda") * x).sum().backward()
                st["q"] += 1; st["cands"] += len(sc)
                del kv
            pol.step()
            step += 1
            rec = {"step": step, "epoch": e + 1, "requests": st["q"], "candidates": st["cands"], "loss": st["loss"] / st["q"],
                   "pair_acc": st["pairs_ok"] / st["q"], "t": round(time.time() - t0)}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            if step % save == 0:
                pol.model.save_pretrained(f"{out}/adapter_s{step}")
    pol.model.save_pretrained(f"{out}/adapter_final")
    print("done", out, step, "steps", flush=True)


def main():
    out = sys.argv[1]
    if "--orm" in sys.argv:
        return main_orm(out)
    nq, B, G, lr, smoke = arg("--questions", 6000), arg("--batch", 64), arg("--group", 8), arg("--lr", 2e-5), arg("--smoke", 0)
    base = arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B")
    bil = json.load(open(arg("--bil", ""))) if "--bil" in sys.argv else None
    plus = "--plus" in sys.argv
    os.makedirs(out, exist_ok=True)
    items = [json.loads(l) for l in open(ITEMS)]
    random.Random(0).shuffle(items)
    items = items[:smoke or nq]
    print(f"tc c1: {len(items)} training requests, batch {B}, group {G}, lr {lr}" + (f", cascade reward x {bil['_scale']:.2f}" if bil and not plus
          else "") + (", right + cascade reward" if plus else ""), flush=True)
    pol = Policy(base, lr)
    log = open(f"{out}/log.jsonl", "a")
    model_name = "local"   # round 0: the adapter is zero, the base model samples
    for rnd, a in enumerate(range(0, len(items), B)):
        t0 = time.time()
        batch = items[a:a + B]
        msgs = [[{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}] for p in batch]
        with ThreadPoolExecutor(32) as ex:
            drafts = list(ex.map(lambda m: sample(model_name, m, G, MAXQ, random.randrange(1 << 30)), msgs))
        t1 = time.time()
        st = {"right": 0.0, "right_call": 0.0, "n_call": 0, "right_none": 0.0, "n_none": 0, "n": 0, "w": 0.0, "agree": 0.0}
        for qi, p in enumerate(batch):
            ds = drafts[qi]
            R = [right(d, p["gold"], p["functions"]) for d in ds]
            st["right"] += sum(R); st["n"] += G
            k = "call" if p["gold"] else "none"
            st[f"right_{k}"] += sum(R); st[f"n_{k}"] += G
            W = R
            if bil is not None:
                b = bil.get(p["id"])
                W = [0.0 if b is None or not check(d, p["functions"]) else
                     b["px"].get(canon(d), 0.0) * (r - b["rD"] + 0.005 * b["kd"]) for d, r in zip(ds, R)]
                st["w"] += sum(W)
                W = [r + w for r, w in zip(R, W)] if plus else [bil["_scale"] * w for w in W]
                st["agree"] += 0 if b is None else sum(b["px"].get(canon(d), 0.0) for d in ds if check(d, p["functions"]))
            mu = sum(W) / G
            A = [x - mu for x in W]
            if any(abs(x) > 1e-9 for x in A):
                P = pol.ids(msgs[qi])
                kv = pol.prefix(P[:-1])
                comps = [pol.tok(d, add_special_tokens=False)["input_ids"][:MAXQ] + [pol.end] for d in ds]
                for sub, lp in pol.turn1_logp(kv, P, comps):
                    adv = pol.torch.tensor([A[b] for b in sub], device="cuda")
                    (-(adv * lp).sum() / (G * len(batch) * MAXQ)).backward()
                del kv
        pol.step()
        t2 = time.time()
        ad = f"{out}/adapter_r{rnd + 1}"
        pol.model.save_pretrained(ad)
        name = f"tc_r{rnd + 1}"
        r = post("/v1/load_lora_adapter", {"lora_name": name, "lora_path": os.path.abspath(ad)})
        if model_name != "local":
            post("/v1/unload_lora_adapter", {"lora_name": model_name})
            old = f"{out}/adapter_r{rnd}"
            if rnd % 10 != 0 and os.path.isdir(old):
                for f in os.listdir(old):
                    os.remove(os.path.join(old, f))
                os.rmdir(old)
        model_name = name
        rec = {"round": rnd + 1, "requests": a + len(batch), "right": st["right"] / st["n"],
               "right_call": st["right_call"] / max(1, st["n_call"]), "right_none": st["right_none"] / max(1, st["n_none"]),
               **({"w": st["w"] / st["n"], "agree": st["agree"] / st["n"]} if bil else {}),
               "t_sample": round(t1 - t0), "t_train": round(t2 - t1), "load": str(r)[:80]}
        log.write(json.dumps(rec) + "\n"); log.flush()
        print(json.dumps(rec), flush=True)
    pol.model.save_pretrained(f"{out}/adapter_final")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
