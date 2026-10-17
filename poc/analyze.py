"""Summaries for the PoC result files.  usage: analyze.py hack|perturb <model_tag>"""
import json
import sys
from collections import Counter, defaultdict

import numpy as np

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


def boot_ci(per_item, n=2000, seed=0):
    """Cluster bootstrap over problems (samples within a problem are correlated)."""
    rng = np.random.default_rng(seed)
    v = np.array(per_item)
    if len(v) == 0:
        return (float("nan"),) * 2
    bs = rng.choice(v, size=(n, len(v)), replace=True).mean(1)
    return tuple(np.percentile(bs, [2.5, 97.5]))


def hack(tag):
    rows = [json.loads(l) for l in open(f"{RES}/hack_{tag}.jsonl")]
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["strategy"]][r["name"]].append(r)
    names = sorted({r["name"] for r in rows})
    print(f"model={tag}  items={len(names)}  rows={len(rows)}")
    print(f"{'strategy':9s} {'hack@1':>7s} {'95%CI':>13s} {'any@k':>6s} {'invalid':>8s} {'crash':>6s} {'same':>6s} {'trunc':>6s} {'out_tok':>7s}")
    for s in ("blind", "direct", "direct_placebo", "bugfirst", "stress_blind", "stress_placebo", "stress"):
        if s not in by:
            continue
        per = [np.mean([x["verdict"] == "hack" for x in by[s][n]]) for n in names if n in by[s]]
        anyk = np.mean([any(x["verdict"] == "hack" for x in by[s][n]) for n in names if n in by[s]])
        c = Counter(x["verdict"] for n in by[s] for x in by[s][n])
        tot = sum(c.values())
        lo, hi = boot_ci(per)
        trunc = np.mean([x["finish"] == "length" for n in by[s] for x in by[s][n]])
        tok = np.mean([x["out_tokens"] for n in by[s] for x in by[s][n]])
        print(f"{s:9s} {np.mean(per):7.3f} [{lo:.2f},{hi:.2f}] {anyk:6.3f} {c['invalid']/tot:8.3f} "
              f"{c['buggy_crash']/tot:6.3f} {c['same']/tot:6.3f} {trunc:6.3f} {tok:7.0f}")
    for st in ("stress_blind", "stress"):
        hits = [x["first_hit"] for n in by.get(st, {}) for x in by[st][n] if x["verdict"] == "hack"]
        if hits:
            print(f"{st}: generator calls until first hack  median={np.median(hits):.0f}  "
                  f"<=1:{np.mean(np.array(hits) <= 1):.2f}  <=10:{np.mean(np.array(hits) <= 10):.2f}")
    # rating split
    rating = {r["name"]: r["rating"] for r in rows}
    med = np.median(list(rating.values()))
    for s in by:
        lo_ = [np.mean([x["verdict"] == "hack" for x in by[s][n]]) for n in by[s] if rating[n] <= med]
        hi_ = [np.mean([x["verdict"] == "hack" for x in by[s][n]]) for n in by[s] if rating[n] > med]
        print(f"  {s:9s} rating<={med:.0f}: {np.mean(lo_):.3f} (n={len(lo_)})   >{med:.0f}: {np.mean(hi_):.3f} (n={len(hi_)})")
    # paired: does seeing the code help?
    for a, b in (("blind", "direct"), ("direct", "bugfirst"), ("direct", "stress"), ("stress_blind", "stress"), ("stress_placebo", "stress"), ("stress_blind", "stress_placebo")):
        if a in by and b in by:
            common = [n for n in names if n in by[a] and n in by[b]]
            d = [np.mean([x["verdict"] == "hack" for x in by[b][n]]) - np.mean([x["verdict"] == "hack" for x in by[a][n]]) for n in common]
            lo, hi = boot_ci(d)
            print(f"paired {b} - {a}: {np.mean(d):+.3f} [{lo:+.2f},{hi:+.2f}]  (n={len(common)})")


def _contains_seq(hay, needle):
    n = len(needle)
    return n == 0 or any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def perturb_validity(source="eval"):
    """Problems where exact-match judging or the rewrite is invalid:
    multi_answer : statement allows several correct outputs (needs a special checker, exact match is wrong)
    io_broken    : a rewrite no longer contains the original example input verbatim (e.g. it renamed the
                   input alphabet A/B/C -> X/Y/Z), so the original tests no longer match the statement."""
    import re
    sys.path.insert(0, f"{ROOT}/poc")
    from run_perturb import load
    items = {it["name"]: it for it in load(10**9, 10**9, source)}
    rw = json.load(open(f"{RES}/perturb_rewrites.json" if source == "eval" else f"{RES}/perturb_rewrites_{source}.json"))
    bad = {}
    for n, it in items.items():
        if re.search(r"any of them|print any|multiple (possible )?(answers|solutions)|any (valid|correct) answer", it["desc"], re.I):
            bad[n] = "multi_answer"
            continue
        ex = it["tests"][0][0].split()
        for v in ("story", "formal"):
            t = rw.get(f"{n}|{v}")
            if t is not None and not _contains_seq(t.split(), ex):
                bad[n] = f"io_broken:{v}"
    return bad


def perturb(tag, strict=True, source="eval"):
    rows = [json.loads(l) for l in open(f"{RES}/perturb_{tag}.jsonl")]
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["version"]][r["name"]].append(r["verdict"] == "ac")
    names = sorted(set.intersection(*[set(by[v]) for v in by]))
    bad = perturb_validity(source)
    excl = Counter(bad[n].split(":")[0] for n in names if n in bad)
    if strict:
        names = [n for n in names if n not in bad]
    print(f"model={tag}  paired problems={len(names)}  (strict={strict}, excluded {dict(excl)})")
    for v in ("orig", "story", "formal"):
        per = [np.mean(by[v][n]) for n in names]
        lo, hi = boot_ci(per)
        c = Counter(r["verdict"] for r in rows if r["version"] == v)
        print(f"  {v:7s} pass@1={np.mean(per):.3f} [{lo:.2f},{hi:.2f}]  verdicts={dict(c)}")
    for v in ("story", "formal"):
        d = [np.mean(by[v][n]) - np.mean(by["orig"][n]) for n in names]
        lo, hi = boot_ci(d)
        flips_down = sum(np.mean(by["orig"][n]) > 0 and np.mean(by[v][n]) == 0 for n in names)
        flips_up = sum(np.mean(by["orig"][n]) == 0 and np.mean(by[v][n]) > 0 for n in names)
        print(f"  {v:7s} - orig: {np.mean(d):+.3f} [{lo:+.2f},{hi:+.2f}]  solved->unsolved {flips_down}, unsolved->solved {flips_up}")


def exec_(tag):
    rows = [json.loads(l) for l in open(f"{RES}/exec_{tag}.jsonl")]
    cell = defaultdict(list)
    gold = defaultdict(list)
    for r in rows:
        cell[(r["task"], r["n"], r["mode"])].append(r)
    for r in rows:
        if r["mode"] == "direct":
            gold[(r["task"], r["n"])].append(r["gold"])
    tasks = sorted({r["task"] for r in rows}); sizes = sorted({r["n"] for r in rows})
    modes = [m for m in ("direct", "cot", "code") if any(r["mode"] == m for r in rows)]
    print(f"model={tag}  accuracy (n_inst per cell in parens); 'maj'=always-guess-most-common-answer baseline")
    print(f"{'task':9s} {'n':>3s} " + " ".join(f"{m:>12s}" for m in modes) + f" {'maj':>5s} {'cot_trunc':>9s} {'cot_tok':>7s}")
    for t in tasks:
        for n in sizes:
            g = gold[(t, n)]
            maj = Counter(g).most_common(1)[0][1] / len(g) if g else float("nan")
            accs = []
            for m in modes:
                c = cell[(t, n, m)]
                accs.append(f"{np.mean([x['correct'] for x in c]):.2f} ({len(c):2d})" if c else f"{'-':>12s}")
            cot = cell[(t, n, "cot")]
            tr = np.mean([x["finish"] == "length" for x in cot]) if cot else float("nan")
            tok = np.mean([x["out_tokens"] for x in cot]) if cot else float("nan")
            print(f"{t:9s} {n:3d} " + " ".join(f"{a:>12s}" for a in accs) + f" {maj:5.2f} {tr:9.2f} {tok:7.0f}")
    fails = Counter((r["mode"], "no_pred" if r["pred"] is None else "wrong") for r in rows if not r["correct"])
    print("failure kinds:", dict(fails))


def compress():
    """PoC #7 table: one row per compression config (PPL/KL vs task metrics, agreement with the Q8_0 reference)."""
    import os
    import re
    tags = ["q8_0-kvf16", "q4km-kvf16", "q3km-kvf16", "q2k-kvf16", "q4km-kvq8", "q4km-kvq4"]

    def load(path):
        return [json.loads(l) for l in open(path)] if os.path.exists(path) else []
    ref = {(r["task"], r["n"], r["inst"]): r for r in load(f"{RES}/exec_c_q8_0-kvf16.jsonl") if r["mode"] == "cot" and r["n"] <= 12}
    print(f"{'config':12s} {'PPL':>6s} {'KLD':>7s} {'top1%':>6s} {'cot':>5s} {'agreeQ8':>7s} {'cot_tok':>7s} {'trunc':>5s} {'code':>5s} {'hack@1':>6s} {'solve':>5s}")
    for t in tags:
        txt = open(f"{RES}/ppl_{t}.txt").read() if os.path.exists(f"{RES}/ppl_{t}.txt") else ""
        ppl = re.findall(r"Final estimate: PPL = ([\d.]+)", txt) or re.findall(r"Mean PPL\(Q\)\s+:\s+([\d.]+)", txt)
        kld = re.findall(r"Mean\s+KLD:\s+([\d.]+)", txt)
        top = re.findall(r"Same top p:\s+([\d.]+)", txt)
        ex = [r for r in load(f"{RES}/exec_c_{t}.jsonl") if r["n"] <= 12]
        cot = [r for r in ex if r["mode"] == "cot"]; code = [r for r in ex if r["mode"] == "code"]
        agree = [r["pred"] == ref[(r["task"], r["n"], r["inst"])]["pred"] for r in cot if (r["task"], r["n"], r["inst"]) in ref]
        hk = load(f"{RES}/hack_c_{t}.jsonl")
        hb = defaultdict(list)
        for r in hk:
            hb[r["name"]].append(r["verdict"] == "hack")
        sv = load(f"{RES}/perturb_c_{t}.jsonl")
        f = lambda xs: f"{np.mean(xs):.2f}" if len(xs) else "  -"
        tok = f"{np.mean([r['out_tokens'] for r in cot]):.0f}" if cot else "-"
        print(f"{t:12s} {(ppl[-1] if ppl else '-'):>6s} {(kld[-1] if kld else '-'):>7s} {(top[-1] if top else '-'):>6s} "
              f"{f([r['correct'] for r in cot]):>5s} {f(agree):>7s} {tok:>7s} "
              f"{f([r['finish'] == 'length' for r in cot]):>5s} {f([r['correct'] for r in code]):>5s} "
              f"{f([np.mean(v) for v in hb.values()]):>6s} {f([r['verdict'] == 'ac' for r in sv]):>5s}"
              f"   (n cot={len(cot)}, hack items={len(hb)}, solve={len(sv)})")


if __name__ == "__main__":
    if sys.argv[1] == "perturb":
        src = sys.argv[3] if len(sys.argv) > 3 else "eval"
        perturb(sys.argv[2], strict=False, source=src)
        perturb(sys.argv[2], strict=True, source=src)
    elif sys.argv[1] == "compress":
        compress()
    elif sys.argv[1] == "exec":
        exec_(sys.argv[2])
    else:
        hack(sys.argv[2])
