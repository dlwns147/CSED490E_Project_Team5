"""CV-1 (docs/prereg/PREREG_CV.md): RL on Qwen3-8B's non-thinking mode for the value of the cascade
  quick query (turn 1) -> free check -> turn 2: the query's result, ACCEPT or DEFER -> on a failed check or DEFER, the base model's T->T.
Arms: cv (both turns trained; turn 1 may reply DEFER), c1 (turn 1 only, no DEFER, reward = the query right: plain RL), c2 (turn 1 is
the base model, only turn 2 trained). One vLLM server (base + the current adapter, reloaded each round) on GPU 0, the trainer (LoRA,
transformers + peft) on the next GPU. Turn 2 is trained on its exact expected reward over {ACCEPT, DEFER} (both outcomes are known
for every query); turn 1 by policy gradient with the group mean as the baseline (G samples per question), a passing query's value
being the gate's expected reward. The prompt's keys and values carry no gradient (computed under the current adapter).
Reward (accuracy units, LAM per 1k output tokens = SQL-1's 0.5 utility points): answer = right - LAM * k_quick; escalate =
v(x) - LAM * (k_quick + c(x)), with v / c the base model's T->T on that training question (grades of tag q8btrain, seeds 1 / 2).
usage: /opt/conda/bin/python cv_train.py <cv|c1|c2> <out dir> [--questions 6000] [--batch 64] [--group 8] [--lr 2e-5] [--smoke N]
  (POC_BASE_URL: a vLLM server started with --enable-lora and VLLM_ALLOW_RUNTIME_LORA_UPDATING=True; SQL_SPLIT=train is set here)"""
import hashlib, json, os, random, sqlite3, sys, time, urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

os.environ.setdefault("SQL_SPLIT", "train")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prep_sql import ITEMS, db_path, extract  # noqa: E402

BASE_URL = os.environ.get("POC_BASE_URL", "http://127.0.0.1:8080/v1")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
DEFER_LINE = "If you would need to think step by step to get it right, reply only DEFER."
LAM, TEMP, MAXQ, BUDGET, MAXB = 0.005, 0.7, 512, 512, 1   # quick-query cap in training; new tokens and sequences per gradient chunk
# (one 24 GB GPU: SDPA keeps each sequence's GQA-repeated keys / values of the whole prompt for the backward pass, ~0.6 GB per 1k prompt tokens)
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def prompt1(user, arm):
    return user + ("\n" + DEFER_LINE if arm == "cv" else "")


def is_defer(text):
    return not extract(text) and "DEFER" in (text or "").upper()


def turn2(n, cols, first):
    """what turn 2 shows: row count, column names, the first 5 rows (values cut at 50 characters)"""
    rows = "\n".join("\t".join(r)[:300] for r in first)
    return (f"Running your query returned {n} row{'' if n == 1 else 's'}. The first {len(first)}:\n" + "\t".join(cols)[:300] + f"\n{rows}\n\n"
            "Does this result answer the question? Reply ACCEPT or DEFER.")


def run_query(db, sql, timeout):
    """(check, hash of the result rows as grade_sql.py's digest, column names, row count, first 5 rows); check as prep_sql.check"""
    if not sql.strip():
        return "no query", None, [], 0, []
    con = sqlite3.connect(f"file:{db_path(db)}?mode=ro&immutable=1", uri=True)
    end = time.time() + timeout
    con.set_progress_handler(lambda: time.time() > end, 10000)
    try:
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description or []]
    except Exception as e:
        return ("timeout" if time.time() > end else f"{type(e).__name__}: {e}"[:300]), None, [], 0, []
    finally:
        con.close()
    h = hashlib.md5(repr(sorted(map(repr, set(rows)))).encode()).hexdigest()[:16]
    return ("pass" if rows else "no rows"), h, cols, len(rows), [[str(v)[:50] for v in r] for r in rows[:5]]


def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE_URL.rsplit("/v1", 1)[0] + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except ValueError:
        return {"text": raw.decode(errors="replace")}


def sample(model, msgs, n, max_tokens, seed, temperature=TEMP):
    r = post("/v1/chat/completions", {"model": model, "messages": msgs, "n": n, "temperature": temperature, "top_p": 0.95,
                                      "max_tokens": max_tokens, "seed": seed, "chat_template_kwargs": {"enable_thinking": False}})
    return [c["message"]["content"] or "" for c in r["choices"]]


def rows_of(path):
    out = []
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def think_values(tag="q8btrain"):
    """{id: (v, c)}: the base model's T->T on each training question — T (seed 1), its retry (seed 2) where T's query fails the check;
    questions whose retry is missing are left out"""
    G1 = json.load(open(f"{RES}/grades_{tag}_s1.json"))
    p2 = f"{RES}/grades_{tag}_s2.json"
    G2 = json.load(open(p2)) if os.path.exists(p2) else {}
    T1 = {r["id"]: r for r in rows_of(f"{RES}/{tag}_think_s1.jsonl")}
    T2 = {r["id"]: r for r in rows_of(f"{RES}/{tag}_think_s2.jsonl")}
    V = {}
    for i, g in G1.items():
        if i == "_gold_fail" or "T" not in g or i not in T1:
            continue
        if g["T"]["chk"] == "pass":
            V[i] = (float(g["T"]["ok"]), T1[i]["out_tokens"])
        elif "T" in G2.get(i, {}) and i in T2:
            V[i] = (float(G2[i]["T"]["ok"]), T1[i]["out_tokens"] + T2[i]["out_tokens"])
    return V


def retry_ids(path, tag="q8btrain"):
    """the training questions whose seed-1 think fails the check (they get the retry think, seed 2)"""
    G = json.load(open(f"{RES}/grades_{tag}_s1.json"))
    ids = [i for i, g in G.items() if i != "_gold_fail" and "T" in g and g["T"]["chk"] != "pass"]
    open(path, "w").write("\n".join(ids) + "\n")
    print(len(ids), "of", len(G) - 1, "training thinks fail the check: retry ids in", path, flush=True)


class Policy:
    """Qwen3-8B + LoRA on one GPU; log-probs of completions after a prompt whose keys / values carry no gradient"""

    def __init__(self, base, lr):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(base)
        m = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16, device_map={"": 0})
        self.model = get_peft_model(m, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, task_type="CAUSAL_LM", target_modules=TARGETS))
        self.model.print_trainable_parameters()
        self.opt = torch.optim.AdamW([p for p in self.model.parameters() if p.requires_grad], lr=lr, betas=(0.9, 0.99), weight_decay=0.0)
        self.end = self.tok.convert_tokens_to_ids("<|im_end|>")
        self.pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.end
        self.acc, self.de = self.tok.convert_tokens_to_ids("ACCEPT"), self.tok.convert_tokens_to_ids("DE")

    def ids(self, msgs):
        out = self.tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False, tokenize=True)
        return list(out["input_ids"] if isinstance(out, dict) or hasattr(out, "keys") else out)

    @staticmethod
    def kv(cache):
        if hasattr(cache, "layers"):
            return [(l.keys, l.values) for l in cache.layers]
        if hasattr(cache, "key_cache"):
            return list(zip(cache.key_cache, cache.value_cache))
        return [tuple(x) for x in cache]

    @staticmethod
    def cache(kv):
        from transformers import DynamicCache
        c = DynamicCache()
        for i, (k, v) in enumerate(kv):
            c.update(k, v, i)
        return c

    def prefix(self, ids):
        with self.torch.no_grad():
            return self.kv(self.model(input_ids=self.torch.tensor([ids], device="cuda"), use_cache=True).past_key_values)

    def forward(self, kv, l, seqs):
        """logits for each sequence in seqs (token lists continuing the cached prefix of length l), right-padded, with gradient"""
        torch = self.torch
        B, L = len(seqs), max(map(len, seqs))
        kvB = [(k[:, :, :l].expand(B, -1, -1, -1).contiguous(), v[:, :, :l].expand(B, -1, -1, -1).contiguous()) for k, v in kv]
        inp = torch.tensor([s + [self.pad] * (L - len(s)) for s in seqs], device="cuda")
        att = torch.tensor([[1] * (l + len(s)) + [0] * (L - len(s)) for s in seqs], device="cuda")
        pos = torch.arange(l, l + L, device="cuda")[None].expand(B, -1)
        return self.model(input_ids=inp, attention_mask=att, position_ids=pos, past_key_values=self.cache(kvB), use_cache=True).logits

    @staticmethod
    def packs(lens):
        """index groups whose padded size (count x longest) stays within BUDGET tokens"""
        out, cur = [], []
        for i in sorted(range(len(lens)), key=lambda i: lens[i]):
            if cur and ((len(cur) + 1) * lens[i] > BUDGET or len(cur) >= MAXB):
                out.append(cur); cur = []
            cur.append(i)
        return out + [cur] if cur else out

    def turn1_logp(self, kv, P, comps):
        """sum of log-probs (sampling temperature) of each completion, with gradient, in chunks; yields (index list, tensor)"""
        torch = self.torch
        seqs = [[P[-1]] + c for c in comps]
        for sub in self.packs([len(s) for s in seqs]):
            part = [seqs[b] for b in sub]
            lg = self.forward(kv, len(P) - 1, part)[:, :-1].float() / TEMP
            tgt = torch.tensor([s[1:] + [self.pad] * (lg.shape[1] - len(s) + 1) for s in part], device="cuda")
            m = torch.tensor([[1] * (len(s) - 1) + [0] * (lg.shape[1] - len(s) + 1) for s in part], device="cuda", dtype=torch.float)
            lp = lg.gather(-1, tgt[..., None])[..., 0] - torch.logsumexp(lg, -1)
            yield sub, (lp * m).sum(-1)

    def gate_p(self, kv, P, ctxs):
        """P(ACCEPT) against DEFER's first token at the end of each turn-2 context, with gradient, in chunks"""
        torch = self.torch
        l = 0
        for x in zip(P[:-1], *ctxs):
            if len(set(x)) > 1:
                break
            l += 1
        for sub in self.packs([len(c) - l for c in ctxs]):
            part = [ctxs[b][l:] for b in sub]
            lg = self.forward(kv, l, part)
            last = torch.stack([lg[b, len(s) - 1, [self.acc, self.de]].float() for b, s in enumerate(part)])
            del lg
            yield sub, torch.softmax(last, -1)[:, 0]

    def step(self):
        self.torch.nn.utils.clip_grad_norm_([p for p in self.model.parameters() if p.requires_grad], 1.0)
        self.opt.step(); self.opt.zero_grad(set_to_none=True)


def main():
    arm, out = sys.argv[1], sys.argv[2]
    assert arm in ("cv", "c1", "c2"), arm
    nq, B, G, lr, smoke = arg("--questions", 6000), arg("--batch", 64), arg("--group", 8), arg("--lr", 2e-5), arg("--smoke", 0)
    base = arg("--base", "/SSD/huggingface/Qwen/Qwen3-8B")
    os.makedirs(out, exist_ok=True)
    pool = ProcessPoolExecutor(int(os.environ.get("CV_WORKERS", 6)))
    list(pool.map(abs, range(64)))   # start the workers before CUDA is initialised (fork)
    V = think_values() if not smoke else {}
    items = [json.loads(l) for l in open(ITEMS)]
    if smoke:   # engineering smoke: v = 0.5, c = 1,500 tokens for every question
        V = {p["id"]: (0.5, 1500) for p in items}
    items = [p for p in items if p["id"] in V]
    random.Random(0).shuffle(items)
    items = items[:smoke or nq]
    print(f"{arm}: {len(items)} training questions, batch {B}, group {G}, lr {lr}", flush=True)
    pol = Policy(base, lr)
    log = open(f"{out}/log.jsonl", "a")
    model_name = "local"   # round 0: the adapter is zero (B = 0), the base model samples
    for rnd, a in enumerate(range(0, len(items), B)):
        t0 = time.time()
        batch = items[a:a + B]
        msgs1 = [[{"role": "user", "content": prompt1(p["user"], arm)}] for p in batch]
        gen = "local" if arm == "c2" else model_name
        with ThreadPoolExecutor(32) as ex:
            drafts = list(ex.map(lambda m: sample(gen, m, G, MAXQ, random.randrange(1 << 30)), msgs1))
        t1 = time.time()
        jobs = [(qi, j, batch[qi]["db_id"], extract(d)) for qi, ds in enumerate(drafts) for j, d in enumerate(ds)]
        res = dict(zip([(qi, j) for qi, j, _, _ in jobs], pool.map(run_query, [x[2] for x in jobs], [x[3] for x in jobs],
                                                                     [10.0] * len(jobs), chunksize=4)))
        t2 = time.time()
        st = {"defer": 0, "pass": 0, "right": 0, "n": 0, "acc_greedy": 0, "acc_greedy_right": 0, "value_greedy": 0.0}
        for qi, p in enumerate(batch):
            v, c = V[p["id"]]
            ds = drafts[qi]
            k1 = [len(pol.tok(d, add_special_tokens=False)["input_ids"]) + 1 for d in ds]
            P = pol.ids(msgs1[qi])
            kv = pol.prefix(P[:-1])
            right = [res[(qi, j)][1] == p["gold_h"] and res[(qi, j)][0] == "pass" for j in range(G)]
            defer = [arm == "cv" and is_defer(d) for d in ds]
            passing = [res[(qi, j)][0] == "pass" and not defer[j] for j in range(G)]
            esc = lambda k: v - LAM * (k + c) / 1000
            V1 = [esc(k1[j]) for j in range(G)]
            if arm in ("cv", "c2"):   # turn 2: exact expected reward over the two decisions
                idx = [j for j in range(G) if passing[j]]
                ctxs = [pol.ids(msgs1[qi] + [{"role": "assistant", "content": ds[j]},
                                             {"role": "user", "content": turn2(res[(qi, j)][3], res[(qi, j)][2], res[(qi, j)][4])}])
                        for j in idx]
                for sub, pa in pol.gate_p(kv, P, ctxs) if idx else []:
                    ra = pol.torch.tensor([float(right[idx[b]]) - LAM * (k1[idx[b]] + 1) / 1000 for b in sub], device="cuda")
                    rd = pol.torch.tensor([esc(k1[idx[b]] + 1) for b in sub], device="cuda")
                    (-(pa * ra + (1 - pa) * rd).sum() / (G * len(batch))).backward()
                    for b, x, y, z in zip(sub, pa.tolist(), ra.tolist(), rd.tolist()):
                        V1[idx[b]] = x * y + (1 - x) * z
                        st["acc_greedy"] += x >= 0.5; st["acc_greedy_right"] += x >= 0.5 and right[idx[b]]
                        st["value_greedy"] += (y if x >= 0.5 else z) - V1[idx[b]]
            if arm == "c1":
                V1 = [float(r) for r in right]
            st["value_greedy"] += sum(V1)
            st["defer"] += sum(defer); st["pass"] += sum(passing); st["right"] += sum(right); st["n"] += G
            mu = sum(V1) / G
            A = [x - mu for x in V1]
            if arm != "c2" and any(abs(x) > 1e-9 for x in A):
                comps = [pol.tok(d, add_special_tokens=False)["input_ids"][:MAXQ] + [pol.end] for d in ds]
                for sub, lp in pol.turn1_logp(kv, P, comps):
                    adv = pol.torch.tensor([A[b] for b in sub], device="cuda")
                    (-(adv * lp).sum() / (G * len(batch) * MAXQ)).backward()
            del kv
        pol.step()
        t3 = time.time()
        ad = f"{out}/adapter_r{rnd + 1}"
        pol.model.save_pretrained(ad)
        name = f"{arm}_r{rnd + 1}"
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
        rec = {"round": rnd + 1, "questions": a + len(batch), "defer": st["defer"] / n, "pass": st["pass"] / n, "right": st["right"] / n,
               "accept": st["acc_greedy"] / n, "accepted_right": st["acc_greedy_right"] / max(1, st["acc_greedy"]),
               "value": st["value_greedy"] / n, "t_sample": round(t1 - t0), "t_exec": round(t2 - t1), "t_train": round(t3 - t2),
               "load": str(r)[:80]}
        log.write(json.dumps(rec) + "\n"); log.flush()
        print(json.dumps(rec), flush=True)
    pol.model.save_pretrained(f"{out}/adapter_final")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
