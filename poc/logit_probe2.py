"""Logit probe v2 (review item 9): token-level analysis of SAMPLED programs instead of 3 handwritten ones.
For each instance of hull / area2 / close we take the program the model actually sampled with K=0 (only needed helpers) and with K=8
(8 extra helpers), both from the stored n=300 runs (F_geox<m>_dis{0,8}_t07s1, "should use" header), and teacher-force EACH program under
EACH prompt (K0 / K8). Per token we keep the log-prob of the actual token and the top-5 alternatives (approximate entropy).
Reported:
  (1) preference shift, length-normalised: [lp_K8(P8) - lp_K8(P0)] - [lp_K0(P8) - lp_K0(P0)] per token (does the K8 prompt make K8-style code
      more likely than K0-style code, beyond what the K0 prompt does?);
  (2) where the shift sits: Delta_t = lp_K8(t) - lp_K0(t) on the same program, by relative position decile and by region
      (copied helper definitions vs the rest);
  (3) which tokens gain most under K8 (aggregated over programs);
  (4) uncertainty: mean top-5 entropy per program under each prompt (does the toolbox make generation more or less decided?).
usage: POC_BASE_URL=... python logit_probe2.py <model> (model = 8b / 14b / 32b; reads results/geocross_F_geox<model>_dis{0,8}_t07s1.jsonl)"""
import json, math, os, random, re, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import BASE_URL, client  # noqa: E402
import geo_distractors as D  # noqa: E402
import run_geo as G  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
TASKS = ("hull", "area2", "close")


def prompt_text(q, fmt, tb):
    return (f"{q}\n\nDo not compute the answer by hand. Write a Python 3 program that solves this problem for any input in the "
            f"following stdin format: {fmt}. Print only the answer. Give the program in a single ```python code block. Only the "
            f"Python standard library is available (no third-party packages such as shapely or numpy).\n\n{tb}")


def tokenize(text):
    r = requests.post(BASE_URL.rsplit("/v1", 1)[0] + "/tokenize", json={"model": "local", "prompt": text, "add_special_tokens": False}, timeout=600)
    return r.json()["tokens"]


def score(prefix, completion):
    """per completion token: (token_str, logprob, approx entropy from top-5)"""
    full = prefix + completion
    ids, n_pre = tokenize(full), len(tokenize(prefix))
    r = client.completions.create(model="local", prompt=full, max_tokens=1, temperature=0, extra_body={"prompt_logprobs": 5})
    plp = r.choices[0].prompt_logprobs
    out = []
    for pos in range(n_pre, len(ids)):
        d = plp[pos]
        if not d:
            continue
        tid = str(ids[pos])
        ent = d.get(tid) or d.get(ids[pos])
        lp = (ent["logprob"] if isinstance(ent, dict) else ent.logprob) if ent is not None else None
        tops = sorted(((v["logprob"] if isinstance(v, dict) else v.logprob) for v in d.values()), reverse=True)[:5]
        p = np.exp(tops); rest = max(0.0, 1 - p.sum())
        H = float(-(p * tops).sum() - (rest * math.log(rest) if rest > 1e-12 else 0.0))   # lower bound-ish: top-5 + lumped tail
        tok = (ent["decoded_token"] if isinstance(ent, dict) else ent.decoded_token) if ent is not None else "?"
        out.append((tok, lp, H))
    return out


def helper_span(code, helper_names):
    """character spans of copied helper definitions (def NAME ... until the next top-level line)"""
    spans = []
    for m in re.finditer(r"^def (\w+)\(.*?(?=^\S|\Z)", code, re.S | re.M):
        if m.group(1) in helper_names:
            spans.append((m.start(), m.end()))
    return spans


def main():
    m = sys.argv[1]
    rows = {k: {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f"{RES}/geocross_F_geox{m}_dis{k}_t07s1.jsonl"))} for k in (0, 8)}
    jobs = []
    for key in sorted(rows[0]):
        task, n, i = key
        if task not in TASKS or not rows[0][key].get("code") or not rows[8].get(key, {}).get("code"):
            continue
        rng = random.Random(f"{task}-{n}-{i}")
        V = G.variants(task, G.base_instance(task, n, rng), rng)
        q, _, fmt = G.render(task, V["identity"])
        tb = {k: D.toolbox(task, k, "related", random.Random(f"{task}-{n}-{i}-tb"))[0] for k in (0, 8)}
        jobs.append((key, q, fmt, tb, {k: rows[k][key] for k in (0, 8)}))

    def run(j):
        key, q, fmt, tb, progs = j
        res = {"key": key, "class": {k: progs[k]["class"] for k in (0, 8)}}
        names = set(D.RELATED)
        for pk in (0, 8):
            code = progs[pk]["code"].strip() + "\n"
            spans = helper_span(code, names)
            for ck in (0, 8):
                head = f"<|im_start|>user\n{prompt_text(q, fmt, tb[ck])}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n```python\n"
                toks = score(head, code + "```")
                # map tokens to char offsets to flag helper-definition region
                pos, flags = 0, []
                for t, _, _ in toks:
                    flags.append(any(a <= pos < b for a, b in spans)); pos += len(t)
                res[f"P{pk}_C{ck}"] = {"tok": [t for t, _, _ in toks], "lp": [l for _, l, _ in toks], "H": [h for _, _, h in toks], "helper": flags}
        return res

    with ThreadPoolExecutor(16) as ex:
        out = list(ex.map(run, jobs))
    json.dump(out, open(f"{RES}/logit_probe2_{m}.json", "w"))

    def mlp(x):
        v = [l for l in x["lp"] if l is not None]; return np.mean(v)
    shift = [(mlp(o["P8_C8"]) - mlp(o["P0_C8"])) - (mlp(o["P8_C0"]) - mlp(o["P0_C0"])) for o in out]
    print(f"[{m}] n={len(out)} programs per condition (tasks {TASKS})")
    print(f"(1) preference shift per token (K8-style vs K0-style code, K8 prompt minus K0 prompt): {np.mean(shift):+.4f} nats/token "
          f"(>0 in {np.mean(np.array(shift) > 0):.0%} of instances)")
    for pk in (0, 8):
        print(f"    P{pk} mean lp/token: under K0 {np.mean([mlp(o[f'P{pk}_C0']) for o in out]):.4f} | under K8 {np.mean([mlp(o[f'P{pk}_C8']) for o in out]):.4f}")
    # (2) where: delta by decile and region, on each program
    for pk in (0, 8):
        dec = defaultdict(list); reg = defaultdict(list)
        for o in out:
            a, b = o[f"P{pk}_C8"], o[f"P{pk}_C0"]
            L = min(len(a["lp"]), len(b["lp"]))
            for t in range(L):
                if a["lp"][t] is None or b["lp"][t] is None:
                    continue
                d = a["lp"][t] - b["lp"][t]
                dec[int(10 * t / L)].append(d); reg["helper-def" if a["helper"][t] else "own code"].append(d)
        print(f"(2) P{pk}: Delta lp (K8 - K0 prompt) by position decile: " + " ".join(f"{np.sum(dec[k]) / len(out):+.2f}" for k in range(10))
              + " (nats per program) | by region: " + ", ".join(f"{k} {np.sum(v) / len(out):+.2f} ({len(v)} tok)" for k, v in reg.items()))
    # (3) tokens gaining most under K8 (on K8-sampled programs, own code only)
    gain = defaultdict(list)
    for o in out:
        a, b = o["P8_C8"], o["P8_C0"]
        for t in range(min(len(a["lp"]), len(b["lp"]))):
            if a["lp"][t] is not None and b["lp"][t] is not None and not a["helper"][t]:
                gain[a["tok"][t].strip()].append(a["lp"][t] - b["lp"][t])
    top = sorted(((np.sum(v), k, len(v)) for k, v in gain.items() if len(v) >= 5), reverse=True)[:15]
    print("(3) tokens with the largest total log-prob gain under K8 (own code of K8 programs): " + ", ".join(f"{k!r} {s:+.1f} (n={c})" for s, k, c in top))
    # (4) entropy
    for pk in (0, 8):
        print(f"(4) P{pk}: mean top-5 entropy per token under K0 {np.mean([np.mean(o[f'P{pk}_C0']['H']) for o in out]):.4f} | "
              f"under K8 {np.mean([np.mean(o[f'P{pk}_C8']['H']) for o in out]):.4f}")


if __name__ == "__main__":
    main()
