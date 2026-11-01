"""WP-RL (docs/prereg/PREREG_WPRL.md): plain RL on Qwen3-8B's non-thinking programs for optimization word problems — CV-1's C1 loop
(poc/cv_train.py: LoRA r 16, GRPO without std normalisation, 8 samples per problem, 64 problems per round, one optimizer step per round,
lr 2e-5, no KL) on OptMATH-Train problems ($POC_DATA/optmath_train/wp_train_items.jsonl, poc/prep_wptrain.py) in the held-out sets'
cheap prompt (run_nlopt.P_FREE: solver of the model's choice), reward = the program's printed value is the gold optimum (run_nlopt.correct,
the program run in the sandbox as run_nlopt does: 60 s, 4 GB). Programs are sampled up to CAP tokens (a longer one is cut, so it
fails). One vLLM server (base + the current adapter, reloaded each round) on GPU 0, the trainer on GPU 1 (poc/slurm/wp_lane.sh).
usage: /opt/conda/bin/python wp_train.py <out dir> [--questions 4000] [--batch 64] [--group 8] [--lr 2e-5] [--smoke N]
       (POC_PYTHON: the sandbox python with OR-Tools / cvxpy / scipy)
--orm (PREREG_LCM addendum SEL-W): no sampling; SEL's within-question verifier on VER's programs — Qwen3-8B's stored OptMATH-Train
programs (td rows q8b / q8bq2: 8 quick, the cut think, the full think), VER's training problems only (crc32(id) % 10 != 0), passing
programs grouped by value (run_nlopt.correct either way), problems with a right and a wrong value; context = VER's prompt
(ver_build.prompt), score s = logit(yes) - logit(no) of the first answer token, per problem the mean over (right, wrong) value pairs of
log(1 + exp(s_w - s_r)); at most 8 values per problem, one program per value drawn per epoch.
       /opt/conda/bin/python wp_train.py <out dir> --orm [--batch 16] [--lr 5e-5] [--epochs 2] [--save 25] [--smoke N]"""
import json, os, random, re, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cv_train import Policy, arg, post, sample  # noqa: E402
from run_nlopt import P_FREE, correct, value_of  # noqa: E402
from sandbox import run_python  # noqa: E402

ITEMS = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "optmath_train", "wp_train_items.jsonl")
CAP = 1536


def last_block(text, langs):   # as llm.last_block (the training python has no openai client)
    blocks = [b for lang, b in re.findall(r"```([a-zA-Z0-9_+-]*)[ \t]*\n(.*?)```", text, flags=re.S) if lang.lower() in langs and b.strip()]
    if blocks:
        return blocks[-1]
    for lang in [l for l in langs if l]:
        i = text.rfind(f"```{lang}\n")
        if i >= 0:
            body = text[i + len(lang) + 4:]
            j = body.find("```")
            return body[:j] if j >= 0 else body
    return None


def grade(text, gold):
    """(runs and prints a value, right)"""
    code = last_block(text or "", ("python", "py", "python3"))
    if not code:
        return False, False
    r = run_python(code, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600)
    lines = [l for l in (r.stdout if r.status == "ok" else "").strip().splitlines() if l.strip()]
    pred = value_of(lines[-1]) if lines else None
    return pred is not None, correct(pred, gold)


def main_orm(out):
    """addendum SEL-W: the word-problem verifier (see the docstring)"""
    import glob, math, zlib
    from ver_build import passes, prompt
    D = os.path.dirname(ITEMS)
    B, lr, ep, save, smoke = arg("--batch", 16), arg("--lr", 5e-5), arg("--epochs", 2), arg("--save", 25), arg("--smoke", 0)
    os.makedirs(out, exist_ok=True)
    Qt = {p["id"]: p["q"] for p in map(json.loads, open(ITEMS))}
    R = {r["id"]: r for t in ("q8b", "q8bq2") for f in sorted(glob.glob(f"{D}/td/td_{t}_p*.jsonl")) for r in map(json.loads, open(f))}
    same = lambda a, b: correct(a, str(b)) or correct(b, str(a))
    Q = []
    for i, r in sorted(R.items()):
        if zlib.crc32(i.encode()) % 10 == 0:   # VER's train-dev problems: never trained on
            continue
        g = []   # [value, right, [programs]]
        for x in list(r["quick"]) + [r[a] for a in ("sb", "t") if r.get(a)]:
            if not passes(x):
                continue
            v = value_of(str(x["pred"]))
            k = next((y for y in g if same(v, y[0])), None)
            if k is None:
                g.append([v, str(x["right"]) == "True", []]); k = g[-1]
            k[2].append(x)
        if any(y[1] for y in g) and not all(y[1] for y in g):
            Q.append((i, [y for y in g if y[1]], [y for y in g if not y[1]]))
    random.Random(0).shuffle(Q)
    Q = Q[:smoke or len(Q)]
    print(f"orm-w: {len(Q)} problems with a right and a wrong passing value (of {len(R)}), {sum(len(r) + len(w) for _, r, w in Q)} "
          f"values; batch {B}, lr {lr}, epochs {ep}", flush=True)
    pol = Policy(arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B"), lr)
    pol.acc, pol.de = pol.tok.convert_tokens_to_ids("yes"), pol.tok.convert_tokens_to_ids("no")   # VER's answer words
    assert isinstance(pol.acc, int) and isinstance(pol.de, int) and pol.acc != pol.de, (pol.acc, pol.de)
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
            for i, Rg, Wg in batch:
                gs = [(y, True) for y in Rg] + [(y, False) for y in Wg]
                if len(gs) > 8:   # at most 8 values: one right, one wrong, the rest drawn
                    rest = gs[1:len(Rg)] + gs[len(Rg) + 1:]
                    gs = [gs[0], gs[len(Rg)]] + rng.sample(rest, 6)
                ctxs, lab = [], []
                for y, ok in gs:
                    x = rng.choice(y[2])
                    ctxs.append(pol.ids([{"role": "user", "content": prompt(Qt[i], x["code"], x["pred"])}]))
                    lab.append(ok)
                P = pol.ids([{"role": "user", "content": Qt[i].strip()}])   # the shared prefix: the problem statement
                kv = pol.prefix(P[:-1])
                s = [0.0] * len(ctxs)
                with torch.no_grad():
                    for sub, x in pol.gate_p(kv, P, ctxs, logit=True):
                        for b, v in zip(sub, x.tolist()):
                            s[b] = v
                pr = [(r, w) for r in range(len(s)) if lab[r] for w in range(len(s)) if not lab[w]]
                g = [0.0] * len(s)
                for r, w in pr:
                    sg = 1.0 / (1.0 + math.exp(s[r] - s[w]))   # d/d(s_w - s_r) of log(1 + exp(s_w - s_r))
                    g[w] += sg / len(pr) / len(batch); g[r] -= sg / len(pr) / len(batch)
                    st["loss"] += math.log1p(math.exp(s[w] - s[r])) / len(pr) if s[w] - s[r] < 30 else (s[w] - s[r]) / len(pr)
                    st["pairs_ok"] += ((s[r] > s[w]) + 0.5 * (s[r] == s[w])) / len(pr)
                for sub, x in pol.gate_p(kv, P, ctxs, logit=True):
                    (torch.tensor([g[b] for b in sub], device="cuda") * x).sum().backward()
                st["q"] += 1; st["cands"] += len(s)
                del kv
            pol.step()
            step += 1
            rec = {"step": step, "epoch": e + 1, "problems": st["q"], "candidates": st["cands"], "loss": st["loss"] / st["q"],
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
    nq, B, G, lr, smoke = arg("--questions", 4000), arg("--batch", 64), arg("--group", 8), arg("--lr", 2e-5), arg("--smoke", 0)
    base = arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B")
    os.makedirs(out, exist_ok=True)
    items = [json.loads(l) for l in open(ITEMS)]
    random.Random(0).shuffle(items)
    items = items[:smoke or nq]
    print(f"wp c1: {len(items)} training problems, batch {B}, group {G}, lr {lr}, cap {CAP}", flush=True)
    pol = Policy(base, lr)
    log = open(f"{out}/log.jsonl", "a")
    model_name = "local"   # round 0: the adapter is zero, the base model samples
    ex = ThreadPoolExecutor(int(os.environ.get("WP_WORKERS", 8)))
    for rnd, a in enumerate(range(0, len(items), B)):
        t0 = time.time()
        batch = items[a:a + B]
        msgs = [[{"role": "user", "content": P_FREE.format(q=p["q"])}] for p in batch]
        with ThreadPoolExecutor(32) as sx:
            drafts = list(sx.map(lambda m: sample(model_name, m, G, CAP, random.randrange(1 << 30)), msgs))
        t1 = time.time()
        jobs = [(qi, d) for qi, ds in enumerate(drafts) for d in ds]
        res = list(ex.map(lambda x: grade(x[1], batch[x[0]]["gold"]), jobs))
        R = [[float(res[qi * G + j][1]) for j in range(G)] for qi in range(len(batch))]
        runs = sum(r[0] for r in res)
        t2 = time.time()
        st = {"right": 0.0, "n": 0, "mixed": 0}
        for qi, p in enumerate(batch):
            ds, W = drafts[qi], R[qi]
            st["right"] += sum(W); st["n"] += G
            mu = sum(W) / G
            A = [x - mu for x in W]
            if any(abs(x) > 1e-9 for x in A):
                st["mixed"] += 1
                P = pol.ids(msgs[qi])
                kv = pol.prefix(P[:-1])
                comps = [pol.tok(d, add_special_tokens=False)["input_ids"][:CAP] + [pol.end] for d in ds]
                for sub, lp in pol.turn1_logp(kv, P, comps):
                    adv = pol.torch.tensor([A[b] for b in sub], device="cuda")
                    (-(adv * lp).sum() / (G * len(batch) * CAP)).backward()
                del kv
        pol.step()
        t3 = time.time()
        ad = f"{out}/adapter_r{rnd + 1}"
        pol.model.save_pretrained(ad)
        name = f"wp_r{rnd + 1}"
        r = post("/v1/load_lora_adapter", {"lora_name": name, "lora_path": os.path.abspath(ad)})
        if model_name != "local":
            post("/v1/unload_lora_adapter", {"lora_name": model_name})
            old = f"{out}/adapter_r{rnd}"
            if rnd % 10 != 0 and os.path.isdir(old):
                for f in os.listdir(old):
                    os.remove(os.path.join(old, f))
                os.rmdir(old)
        model_name = name
        rec = {"round": rnd + 1, "problems": a + len(batch), "right": st["right"] / st["n"], "runs": runs / st["n"],
               "mixed": st["mixed"] / len(batch), "t_sample": round(t1 - t0), "t_exec": round(t2 - t1), "t_train": round(t3 - t2),
               "load": str(r)[:80]}
        log.write(json.dumps(rec) + "\n"); log.flush()
        print(json.dumps(rec), flush=True)
    pol.model.save_pretrained(f"{out}/adapter_final")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
