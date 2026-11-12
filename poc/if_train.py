"""IFRL (docs/prereg/PREREG_IFRL.md): GRL's loop off puzzles. Plain RL on Qwen3-8B's non-thinking response to an instruction-following
prompt (IFEval, IFBench), cross-fitted in two folds (fold = crc32 of the prompt key mod 2; fold f trains on the other fold's prompts and
is evaluated on its own). The loop is gp_train's (LoRA r 16, GRPO without std normalisation, --group samples per prompt, --batch prompts
per round, one optimizer step per round, lr 2e-5, no KL, 4 epochs); responses are sampled up to CAP tokens.
Rewards:
  gold   the benchmark's official strict grader: every instruction of the prompt followed (grade_if.py's prompt-level strict)
  noisy  (IFRL2) gold passed through class-conditional noise with the check's measured rates (--tpr, --fpr): the same J as the check,
         with errors that do not depend on which response it is
  check  the free check, no label: the response passes the model's own checker for the prompt. The checker is fixed before training:
         the one Qwen3-8B wrote at seed 1 in IF-1 (run_if.py, column c_code of results/if/<bench>_q8b_cheap_s1.jsonl, copied to
         $POC_DATA/if_rl/checkers_<bench>.json); it runs in the sandbox as run_if.check does (10 s, 1 GB). No checker or a crash = 0.
usage: /opt/conda/bin/python if_train.py <out dir> <bench> <fold 0|1> [--reward gold|check] [--epochs 4] [--batch 16] [--group 8] [--lr 2e-5]
       python if_train.py --eval <bench> <tag> <seed> [--ids <file>]   (one non-thinking response per prompt from the server's model
           "local", 4,096 tokens, temperature 0.7, as run_if's N; with its fixed-checker result -> results/if/<bench>_<tag>_cheap_s<seed>.jsonl;
           graded afterwards by grade_if.py <bench> <tag> <seed ...>, arm N)
       python if_train.py --ids <bench> <dir>   (writes <dir>/<bench>_fold{0,1}_ids.txt)
IFRL2 (PREREG_IFRL.md, amendment): bench "pool" = 2,000 training prompts of Ai2's IF-RLVR data (allenai/IF_multi_constraints_upto5) whose
constraints are all IFEval's 25 types (18,221 of 95,373; shuffled with seed 0), graded by IFEval's grader; fold "all" trains on the whole
pool (it shares no prompt with either test set), evaluated on all IFEval and IFBench test prompts.
       python if_train.py --checkers <bench>   (the model's checker for every prompt, run_if's CHECKER prompt and 2,000-token think,
           seed 1 -> $POC_DATA/if_rl/checkers_<bench>.json; resumes)
       python if_train.py --sample <bench> <n>   (n base responses per prompt as in training: no thinking, CAP tokens, temperature 0.7,
           with the checker's result -> results/if/<bench>_base_samples.jsonl)
       python if_train.py --jstat <bench>   (gold-grades those samples: TPR, FPR, J, precision, split shares; needs the graders' packages)
       python if_train.py --report <bench> <base tag> <name>=<tag>[+<tag>] ... [--seeds 4,5,6]   (held-out right / own-check pass shares,
           paired 95% bootstrap over prompts)
(POC_PYTHON: the sandbox python; IF_PKGS: a directory with the graders' packages, for the gold reward)"""
import ast, json, os, random, sys, time, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "if")
FILES = {"ifeval": "ifeval_input_data.jsonl", "ifbench": "IFBench_test.jsonl", "pool": "../if_rl/ifmc5_pool.jsonl"}
CAP = 2048   # IF-1's N: 95th percentile 1,049 (IFEval) and 3,472 (IFBench) tokens; 1.4% / 5.7% reach 2,048
_SRC = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_if.py")).read())
RUNNER = next(ast.literal_eval(n.value) for n in _SRC.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "RUNNER")


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def prompts(bench):
    return [dict(json.loads(l), id=str(json.loads(l)["key"])) for l in open(os.path.join(DATA, "ifeval", FILES[bench]))]


def fold_of(i):
    return zlib.crc32(i.encode()) % 2


def checkers(bench):
    return json.load(open(os.path.join(DATA, "if_rl", f"checkers_{bench}.json")))


def check(code, response):   # as run_if.check: 'pass' / 'fail' / 'error'
    if not code:
        return "error"
    r = run_python(code + RUNNER, response or "", timeout=10, mem_bytes=1 << 30)
    try:
        o = json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return "error"
    return "error" if "violations" not in o else ("fail" if o["violations"] else "pass")


class Gold:
    """the official strict grader, prompt level (every instruction followed)"""

    def __init__(self, bench):
        if os.environ.get("IF_PKGS"):
            sys.path.insert(0, os.environ["IF_PKGS"])
        sys.path.insert(0, os.path.join(DATA, "ifeval", "grader_ifeval" if bench == "ifeval" else "grader_ifbench"))
        import nltk
        for r in ("punkt", "punkt_tab"):
            nltk.download(r, quiet=True)
        import evaluation_lib as E
        self.E = E

    def __call__(self, x, response):
        inp = self.E.InputExample(key=x["key"], instruction_id_list=list(x["instruction_id_list"]), prompt=x["prompt"],
                                  kwargs=[dict(k) for k in x["kwargs"]])
        try:
            return all(self.E.test_instruction_following_strict(inp, {x["prompt"]: response}).follow_instruction_list)
        except Exception:
            return False


def evaluate(bench, tag, seed, ids):
    from cv_train import sample
    P = [p for p in prompts(bench) if ids is None or p["id"] in ids]
    C = checkers(bench)
    path = f"{RES}/{bench}_{tag}_cheap_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
    os.makedirs(RES, exist_ok=True)
    out = open(path, "a")

    def one(p):   # run_if's seed for N
        t = sample("local", [{"role": "user", "content": p["prompt"]}], 1, 4096, seed * 1000 + zlib.crc32(p["id"].encode()) % 997)[0]
        return {"id": p["id"], "n_text": t, "c_n": check(C.get(p["id"]), t)}
    with ThreadPoolExecutor(64) as ex:
        for row in ex.map(one, [p for p in P if p["id"] not in done]):
            out.write(json.dumps(row) + "\n"); out.flush()
    print(bench, tag, seed, "done", flush=True)


def write_checkers(bench):
    from llm import last_block
    from run_geo_cross import budget_chat
    from run_if import CHECKER
    path = os.path.join(DATA, "if_rl", f"checkers_{bench}.json")
    C = json.load(open(path)) if os.path.exists(path) else {}
    P = [p for p in prompts(bench) if p["id"] not in C]

    def one(p):   # run_if's checker call at seed 1
        c = budget_chat(CHECKER.format(q=p["prompt"]), 2000, max_tokens=2048, temperature=0.7, seed=1000 + zlib.crc32(p["id"].encode()) % 997,
                        cut_note="I will now write the code.")
        return p["id"], last_block(c["text"] or "", ("python", "py", "python3"))
    with ThreadPoolExecutor(64) as ex:
        for k, (i, code) in enumerate(ex.map(one, P)):
            C[i] = code
            if k % 200 == 199:
                json.dump(C, open(path, "w"))
    json.dump(C, open(path, "w"))
    print(bench, len(C), "checkers,", sum(1 for v in C.values() if v), "with code", flush=True)


def base_samples(bench, n):
    from cv_train import sample
    C = checkers(bench)
    path = f"{RES}/{bench}_base_samples.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
    out = open(path, "a")

    def one(p):
        ts = sample("local", [{"role": "user", "content": p["prompt"]}], n, CAP, 7 * 1000 + zlib.crc32(p["id"].encode()) % 997)
        return {"id": p["id"], "texts": ts, "checks": [check(C.get(p["id"]), t) for t in ts]}
    with ThreadPoolExecutor(32) as ex:
        for row in ex.map(one, [p for p in prompts(bench) if p["id"] not in done]):
            out.write(json.dumps(row) + "\n"); out.flush()
    print(bench, "samples done", flush=True)


def jstat(bench):
    gold = Gold(bench if bench != "pool" else "ifeval")
    P = {p["id"]: p for p in prompts(bench)}
    S = [json.loads(l) for l in open(f"{RES}/{bench}_base_samples.jsonl")]
    n = r = rp = wp = err = sc = sg = 0
    for x in S:
        g = [gold(P[x["id"]], t) for t in x["texts"]]
        ps = [c == "pass" for c in x["checks"]]
        n += len(g); r += sum(g); rp += sum(a and b for a, b in zip(g, ps)); wp += sum(b and not a for a, b in zip(g, ps)); err += x["checks"].count("error")
        sc += 0 < sum(ps) < len(ps); sg += 0 < sum(g) < len(g)
    print(f"{bench}: {len(S)} prompts, {n} samples; right {100 * r / n:.1f}%, TPR {rp / r:.3f}, FPR {wp / (n - r):.3f}, J {rp / r - wp / (n - r):.3f}, "
          f"precision {rp / max(1, rp + wp):.3f}, right : wrong among passing {rp / max(1, wp):.1f}, checker errors {100 * err / n:.1f}%; "
          f"prompts split by the check {100 * sc / len(S):.1f}%, by gold {100 * sg / len(S):.1f}%")


def report(bench, base, arms, seeds):
    P = {p["id"]: p for p in prompts(bench)}
    R = {}
    for arm, tags in [("base", [base])] + arms:
        for tag in tags:
            for s in seeds:
                gp = f"{RES}/grades_{bench}_{tag}_s{s}.json"
                if not os.path.exists(gp):
                    continue
                G = json.load(open(gp))
                for l in open(f"{RES}/{bench}_{tag}_cheap_s{s}.jsonl"):
                    x = json.loads(l)
                    if x["id"] in G and "N" in G[x["id"]]:
                        R[(arm, x["id"], s)] = (all(G[x["id"]]["N"]["strict"]), x["c_n"] == "pass")
    A = ["base"] + [a for a, _ in arms]
    keys = sorted({(i, s) for (_, i, s) in R if all((a, i, s) in R for a in A)})
    print(f"== {bench}: {len(keys)} prompt-seeds ({len({i for i, _ in keys})} prompts of {len(P)}), seeds {seeds}")
    for a in A:
        q = [R[(a, i, s)] for i, s in keys]
        n, r, ps, rp, wp = len(q), sum(x[0] for x in q), sum(x[1] for x in q), sum(x[0] and x[1] for x in q), sum(x[1] and not x[0] for x in q)
        print(f"  {a:6s}: right {100 * r / n:5.1f}%, passes own check {100 * ps / n:5.1f}%, right and passes {100 * rp / n:5.1f}%, "
              f"wrong and passes {100 * wp / n:5.1f}%; J = P(pass | right) - P(pass | wrong) = {rp / max(1, r) - wp / max(1, n - r):.2f}")
    rng = random.Random(0)
    ids = sorted({i for i, _ in keys})
    boots = [[rng.choice(ids) for _ in ids] for _ in range(2000)]
    for a, b in [(a, "base") for a, _ in arms] + ([(arms[1][0], arms[0][0])] if len(arms) > 1 else []):
        per = {}
        for i, s in keys:
            per.setdefault(i, []).append((R[(a, i, s)][0] - R[(b, i, s)][0], (R[(a, i, s)][1] and not R[(a, i, s)][0]) - (R[(b, i, s)][1] and not R[(b, i, s)][0])))
        for k, nm in ((0, "right"), (1, "wrong and passes own check")):
            m = {i: sum(z[k] for z in v) / len(v) for i, v in per.items()}
            d = sorted(100 * sum(m[i] for i in bt) / len(bt) for bt in boots)
            print(f"  {a} - {b}: {nm} {100 * sum(m.values()) / len(m):+.1f} [{d[50]:+.1f}, {d[1949]:+.1f}] points")
    if len(arms) > 1:   # the gain ratio (check gain / gold gain), bootstrap over prompts (PREREG_IFRL IF-P3)
        g, c = arms[0][0], arms[1][0]
        per = {}
        for i, s in keys:
            per.setdefault(i, []).append((R[(g, i, s)][0] - R[("base", i, s)][0], R[(c, i, s)][0] - R[("base", i, s)][0]))
        m = {i: (sum(z[0] for z in v) / len(v), sum(z[1] for z in v) / len(v)) for i, v in per.items()}
        rat = lambda S: sum(m[i][1] for i in S) / sum(m[i][0] for i in S) if sum(m[i][0] for i in S) > 0 else None
        d = [rat(bt) for bt in boots]
        ok = sorted(x for x in d if x is not None)
        q = (lambda k: ok[min(len(ok) - 1, int(k * len(ok)))]) if ok else (lambda k: float("nan"))
        print(f"  ({c} - base) / ({g} - base): {rat(ids) if rat(ids) is not None else float('nan'):.2f} [{q(0.025):.2f}, {q(0.975):.2f}] "
              f"({len(d) - len(ok)} of {len(d)} resamples with no gold gain left out)")


def main():
    if "--ids" in sys.argv and sys.argv[1] == "--ids":
        bench, d = sys.argv[2], sys.argv[3]
        os.makedirs(d, exist_ok=True)
        for f in (0, 1):
            open(f"{d}/{bench}_fold{f}_ids.txt", "w").write("\n".join(p["id"] for p in prompts(bench) if fold_of(p["id"]) == f) + "\n")
        return
    if "--eval" in sys.argv:
        i = sys.argv.index("--eval")
        ids = set(open(sys.argv[sys.argv.index("--ids") + 1]).read().split()) if "--ids" in sys.argv else None
        return evaluate(sys.argv[i + 1], sys.argv[i + 2], int(sys.argv[i + 3]), ids)
    if "--checkers" in sys.argv:
        return write_checkers(sys.argv[sys.argv.index("--checkers") + 1])
    if "--sample" in sys.argv:
        i = sys.argv.index("--sample")
        return base_samples(sys.argv[i + 1], int(sys.argv[i + 2]))
    if "--jstat" in sys.argv:
        return jstat(sys.argv[sys.argv.index("--jstat") + 1])
    if "--report" in sys.argv:
        i = sys.argv.index("--report")
        seeds = [int(x) for x in arg("--seeds", "4,5,6").split(",")]
        arms = [(a.split("=")[0], a.split("=")[1].split("+")) for a in sys.argv[i + 3:] if "=" in a and not a.startswith("--")]
        return report(sys.argv[i + 1], sys.argv[i + 2], arms, seeds)
    from cv_train import Policy, post, sample
    out, bench, F = sys.argv[1], sys.argv[2], (None if sys.argv[3] == "all" else int(sys.argv[3]))
    ep, B, G, lr, smoke = arg("--epochs", 4), arg("--batch", 16), arg("--group", 8), arg("--lr", 2e-5), arg("--smoke", 0)
    rw = arg("--reward", "gold")
    assert rw in ("gold", "check", "noisy")
    tpr, fpr = arg("--tpr", 1.0), arg("--fpr", 0.0)   # noisy: gold passed through class-conditional noise, P(1 | right) = tpr, P(1 | wrong) = fpr
    base = arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B")
    os.makedirs(out, exist_ok=True)
    P = prompts(bench)
    C = checkers(bench)
    gold = Gold(bench if bench != "pool" else "ifeval")
    train = [p for p in P if F is None or fold_of(p["id"]) != F]
    rng = random.Random(2 if F is None else F)
    items = []
    for _ in range(ep):
        e = list(train); rng.shuffle(e); items += e
    items = items[:smoke or len(items)]
    print(f"ifrl {bench} fold {F}: {len(train)} training prompts, {ep} epochs, batch {B}, group {G}, lr {lr}, cap {CAP}, reward {rw}", flush=True)
    pol = Policy(base, lr)
    log = open(f"{out}/log.jsonl", "a")
    model_name = "local"
    ex = ThreadPoolExecutor(int(os.environ.get("WP_WORKERS", 16)))
    for rnd, a in enumerate(range(0, len(items), B)):
        t0 = time.time()
        batch = items[a:a + B]
        msgs = [[{"role": "user", "content": p["prompt"]}] for p in batch]
        with ThreadPoolExecutor(32) as sx:
            drafts = list(sx.map(lambda m: sample(model_name, m, G, CAP, random.randrange(1 << 30)), msgs))
        t1 = time.time()
        jobs = [(qi, d) for qi, ds in enumerate(drafts) for d in ds]
        ck = list(ex.map(lambda x: check(C.get(batch[x[0]]["id"]), x[1]), jobs))
        gd = [gold(batch[qi], d) for qi, d in jobs]
        if rw == "noisy":
            R = [[float(rng.random() < (tpr if gd[qi * G + j] else fpr)) for j in range(G)] for qi in range(len(batch))]
        else:
            R = [[float(gd[qi * G + j] if rw == "gold" else ck[qi * G + j] == "pass") for j in range(G)] for qi in range(len(batch))]
        t2 = time.time()
        st = {"n": len(jobs), "mixed": 0}
        for qi in range(len(batch)):
            ds, W = drafts[qi], R[qi]
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
        name = f"if{bench}{rw}{F}_r{rnd + 1}"
        r = post("/v1/load_lora_adapter", {"lora_name": name, "lora_path": os.path.abspath(ad)})
        if model_name != "local":
            post("/v1/unload_lora_adapter", {"lora_name": model_name})
            old = f"{out}/adapter_r{rnd}"
            if rnd % 10 != 0 and os.path.isdir(old):
                for f in os.listdir(old):
                    os.remove(os.path.join(old, f))
                os.rmdir(old)
        model_name = name
        n = st["n"]
        rec = {"round": rnd + 1, "prompts": a + len(batch), "right": sum(gd) / n, "pass": sum(c == "pass" for c in ck) / n,
               "right_pass": sum(g and c == "pass" for g, c in zip(gd, ck)) / n, "wrong_pass": sum((not g) and c == "pass" for g, c in zip(gd, ck)) / n,
               "error": sum(c == "error" for c in ck) / n, "reward": sum(map(sum, R)) / n, "mixed": st["mixed"] / len(batch),
               "len": sum(len(d) for _, d in jobs) / n, "t_sample": round(t1 - t0), "t_grade": round(t2 - t1), "t_train": round(t3 - t2), "load": str(r)[:60]}
        log.write(json.dumps(rec) + "\n"); log.flush()
        print(json.dumps(rec), flush=True)
    pol.model.save_pretrained(f"{out}/adapter_final")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
