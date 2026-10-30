"""TC-RL (docs/prereg/PREREG_TCRL.md): plain RL on Qwen3-8B's non-thinking tool calls — CV-1's C1 loop (poc/cv_train.py: LoRA r 16,
GRPO without std normalisation, 8 samples per request, 64 requests per round, one optimizer step per round, lr 2e-5, no KL, 512-token
cap) on ToolACE requests in BFCL's prompt format ($POC_DATA/toolace/tc_train_items.jsonl, poc/prep_tctrain.py), reward = the calls
right (poc/tc_reward.py: the gold calls as a multiset, or no call where the gold makes none). One vLLM server (base + the current adapter,
reloaded each round) on GPU 0, the trainer on GPU 1 (poc/slurm/tc_lane.sh).
Addendum 2: --bil <file> (poc/prep_tcbil.py) replaces the reward with the cascade's own, c x [passes the check] x P_X(y|i) (right - r_D(i)
+ 0.005 kd(i)): the gradient of the deployed cascade's utility with the peer X and the default fixed.
usage: /opt/conda/bin/python tc_train.py <out dir> [--questions 6000] [--batch 64] [--group 8] [--lr 2e-5] [--smoke N] [--base DIR]
       [--bil FILE]"""
import json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cv_train import MAXQ, Policy, arg, post, sample  # noqa: E402
from tc_reward import canon, check, right  # noqa: E402

ITEMS = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "toolace", "tc_train_items.jsonl")


def main():
    out = sys.argv[1]
    nq, B, G, lr, smoke = arg("--questions", 6000), arg("--batch", 64), arg("--group", 8), arg("--lr", 2e-5), arg("--smoke", 0)
    base = arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B")
    bil = json.load(open(arg("--bil", ""))) if "--bil" in sys.argv else None
    os.makedirs(out, exist_ok=True)
    items = [json.loads(l) for l in open(ITEMS)]
    random.Random(0).shuffle(items)
    items = items[:smoke or nq]
    print(f"tc c1: {len(items)} training requests, batch {B}, group {G}, lr {lr}" + (f", cascade reward x {bil['_scale']:.2f}" if bil else ""),
          flush=True)
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
                     bil["_scale"] * b["px"].get(canon(d), 0.0) * (r - b["rD"] + 0.005 * b["kd"]) for d, r in zip(ds, R)]
                st["w"] += sum(W)
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
