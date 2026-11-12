"""GRL (docs/prereg/PREREG_GRL.md): plain RL on Qwen3-8B's quick translation of logic grid puzzles written by people (GridPuzzle and
Mitra-Baral), labels used only in training, cross-fitted in two folds so that every test puzzle is translated by a model that never saw it.
The loop is WP-RL's (poc/wp_train.py, from CV-1's poc/cv_train.py): LoRA r 16, GRPO without std normalisation, --group samples per puzzle,
--batch puzzles per round, one optimizer step per round, lr 2e-5, no KL. Prompt = the first round of arm gtr (run_zebra.GP_TR, no thinking);
reward = 1 if the program's solver count is 1 and its grid is the gold (grid_score.score, scoring v2), else 0; the program runs with
run_zebra.GP_SOLVE in the sandbox, as gtr does (30 s, 4 GB). Programs are sampled up to CAP tokens (gtr's first rounds: 95th percentile 795).
Folds (`folds`): test puzzles of both sets, joined with any puzzle whose value set overlaps theirs by Jaccard >= 0.9 (Mitra-Baral has 25
dev-test and 3 test-test copies; Schrader et al. 2512.17093 found the same), fold = crc32 of the component's smallest test id mod 2.
Fold f trains on every puzzle (dev and test, both sets) outside fold f's components and is evaluated on fold f's test puzzles.
PREREG_GRLLF: --reward count1 rewards the free check alone (solver count 1, no label); fold "all" trains on every puzzle, test included
(transductive, label-free only), and is evaluated on all test puzzles.
usage: /opt/conda/bin/python gp_train.py <out dir> <fold 0|1|all> [--reward gold|count1] [--epochs 4] [--batch 16] [--group 8] [--lr 2e-5] [--smoke N]
       python gp_train.py --folds <dir>   (writes <dir>/fold{0,1}_ids.txt: the test puzzles each fold's model is evaluated on)
(POC_PYTHON: the sandbox python with OR-Tools; POC_BASE_URL: vLLM with --enable-lora and VLLM_ALLOW_RUNTIME_LORA_UPDATING=True)"""
import ast, itertools, json, os, random, sys, time, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grid_score import score  # noqa: E402
from sandbox import run_python  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
CAP = 1536
_SRC = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_zebra.py")).read())
# the prompt and solver text of run_zebra, read without importing it (the training python has no openai client)
GP_TR, GP_SOLVE = (next(ast.literal_eval(n.value) for n in _SRC.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == k)
                   for k in ("GP_TR", "GP_SOLVE"))


def puzzles():
    return [dict(json.loads(l), set=s) for s in ("gridpuzzle", "lgp") for l in open(os.path.join(DATA, s, "grid.jsonl"))]


def folds(P=None):
    """{id: fold} for test puzzles, and {id: set of folds whose components hold it} for every puzzle"""
    P = P or puzzles()
    V = [set(str(x).lower() for _, v in r["cats"] for x in v) for r in P]
    par = list(range(len(P)))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    for i, j in itertools.combinations(range(len(P)), 2):
        if P[i]["set"] == P[j]["set"] and len(V[i] & V[j]) / len(V[i] | V[j]) >= 0.9:
            par[find(i)] = find(j)
    comp = {}
    for i in range(len(P)):
        comp.setdefault(find(i), []).append(i)
    fold, held = {}, {}
    for c in comp.values():
        tests = sorted(P[i]["id"] for i in c if P[i]["split"] == "test")
        f = {zlib.crc32(tests[0].encode()) % 2} if tests else set()
        for i in c:
            held[P[i]["id"]] = f
            if P[i]["split"] == "test":
                fold[P[i]["id"]] = next(iter(f))
    return fold, held


def prompt(r):
    gold = {a: v for a, v in r["gold"].items()}
    (first, fv), n = r["cats"][0], len(r["cats"][0][1])
    return GP_TR.format(p=r["puzzle"], cols=", ".join(gold), first=first, fv=", ".join(fv), n=n, f0=fv[0])


def last_block(text, langs):   # as llm.last_block
    import re
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


def grade(text, r):
    """(solver count, right): count -1 when the program fails, as gtr records it"""
    code = last_block(text or "", ("python", "py", "python3"))
    if not code:
        return -1, False
    (first, fv) = r["cats"][0]
    solve = GP_SOLVE.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first))
    res = run_python(code + "\n" + solve, "", timeout=30, mem_bytes=4 << 30)
    try:
        out = json.loads(res.stdout.strip().splitlines()[-1])
    except (AttributeError, IndexError, ValueError):
        return -1, False
    return out["count"], out["count"] == 1 and score(out["grid"], r)[0]


def main():
    if "--folds" in sys.argv:
        d = sys.argv[sys.argv.index("--folds") + 1]
        fold, _ = folds()
        os.makedirs(d, exist_ok=True)
        for f in (0, 1):
            open(f"{d}/fold{f}_ids.txt", "w").write("\n".join(sorted(i for i, g in fold.items() if g == f)) + "\n")
        print({f: sum(g == f for g in fold.values()) for f in (0, 1)}, "test puzzles per fold ->", d)
        return
    from cv_train import Policy, arg, post, sample
    out, F = sys.argv[1], (None if sys.argv[2] == "all" else int(sys.argv[2]))
    ep, B, G, lr, smoke = arg("--epochs", 4), arg("--batch", 16), arg("--group", 8), arg("--lr", 2e-5), arg("--smoke", 0)
    rw = arg("--reward", "gold")
    assert rw in ("gold", "count1") and (F is not None or rw == "count1"), "fold all only with the label-free reward"
    base = arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B")
    os.makedirs(out, exist_ok=True)
    P = puzzles()
    _, held = folds(P)
    train = [r for r in P if F is None or F not in held[r["id"]]]
    rng = random.Random(2 if F is None else F)
    items = []
    for _ in range(ep):
        e = list(train); rng.shuffle(e); items += e
    items = items[:smoke or len(items)]
    print(f"grl fold {F}: {len(train)} training puzzles ({sum(r['set'] == 'gridpuzzle' for r in train)} GridPuzzle), {ep} epochs, "
          f"batch {B}, group {G}, lr {lr}, cap {CAP}, reward {rw}", flush=True)
    pol = Policy(base, lr)
    log = open(f"{out}/log.jsonl", "a")
    model_name = "local"   # round 0: the adapter is zero, the base model samples
    ex = ThreadPoolExecutor(int(os.environ.get("WP_WORKERS", 16)))
    for rnd, a in enumerate(range(0, len(items), B)):
        t0 = time.time()
        batch = items[a:a + B]
        msgs = [[{"role": "user", "content": prompt(r)}] for r in batch]
        with ThreadPoolExecutor(32) as sx:
            drafts = list(sx.map(lambda m: sample(model_name, m, G, CAP, random.randrange(1 << 30)), msgs))
        t1 = time.time()
        jobs = [(qi, d) for qi, ds in enumerate(drafts) for d in ds]
        res = list(ex.map(lambda x: grade(x[1], batch[x[0]]), jobs))
        R = [[float(res[qi * G + j][1] if rw == "gold" else res[qi * G + j][0] == 1) for j in range(G)] for qi in range(len(batch))]
        t2 = time.time()
        st = {"right": sum(ok for _, ok in res), "n": 0, "mixed": 0, "count1": sum(c == 1 for c, _ in res), "fail": sum(c == -1 for c, _ in res)}
        for qi in range(len(batch)):
            ds, W = drafts[qi], R[qi]
            st["n"] += G
            mu = sum(W) / G
            A = [x - mu for x in W]
            if any(abs(x) > 1e-9 for x in A):
                st["mixed"] += 1
                Pi = pol.ids(msgs[qi])
                kv = pol.prefix(Pi[:-1])
                comps = [pol.tok(d, add_special_tokens=False)["input_ids"][:CAP] + [pol.end] for d in ds]
                for sub, lp in pol.turn1_logp(kv, Pi, comps):
                    adv = pol.torch.tensor([A[b] for b in sub], device="cuda")
                    (-(adv * lp).sum() / (G * len(batch) * CAP)).backward()
                del kv
        pol.step()
        t3 = time.time()
        ad = f"{out}/adapter_r{rnd + 1}"
        pol.model.save_pretrained(ad)
        name = f"grl{F}_r{rnd + 1}"
        r = post("/v1/load_lora_adapter", {"lora_name": name, "lora_path": os.path.abspath(ad)})
        if model_name != "local":
            post("/v1/unload_lora_adapter", {"lora_name": model_name})
            old = f"{out}/adapter_r{rnd}"
            if rnd % 10 != 0 and os.path.isdir(old):
                for f in os.listdir(old):
                    os.remove(os.path.join(old, f))
                os.rmdir(old)
        model_name = name
        rec = {"round": rnd + 1, "puzzles": a + len(batch), "right": st["right"] / st["n"], "count1": st["count1"] / st["n"],
               "fail": st["fail"] / st["n"], "mixed": st["mixed"] / len(batch), "t_sample": round(t1 - t0), "t_exec": round(t2 - t1),
               "t_train": round(t3 - t2), "load": str(r)[:80]}
        log.write(json.dumps(rec) + "\n"); log.flush()
        print(json.dumps(rec), flush=True)
    pol.model.save_pretrained(f"{out}/adapter_final")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
