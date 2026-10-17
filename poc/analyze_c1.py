"""C1 analysis (pre-registered in FINDINGS 2026-10-13 12:15): is the model's own confidence (raw log-probs of its sampled tokens) a
label-free program selector? Reads results/geocross_S2_C1_geox<m>_{dis0,dis8,hard}_t07s{1,2,3}.jsonl (run_geo_cross --logprobs).
Scores: (a) mean token log-prob of the whole reply (primary), (b) mean over the code-block tokens, (c) min token log-prob in the code.
(1) AUROC for "correct on all 8 variants", within each task, averaged over tasks (macro; primary) and pooled; 95% bootstrap CI over instances.
(2) Selection among the seeds per instance: mean single sample, max-confidence, MR-select (poc/mr_select.py rule: candidates consistent on
    the 6 metamorphic copies of the given instance, majority vote on the identity output), hybrid (MR-consistent candidates first, vote ties
    and 'no consistent candidate' broken by confidence), oracle-any.
usage: python analyze_c1.py [model=8b] [score=a]"""
import json, os, random, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_geo import base_instance, variants  # noqa: E402
from run_geo_mr import mr_check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
M = sys.argv[1] if len(sys.argv) > 1 else "8b"
SEEDS = (1, 2, 3)


def scores(r):
    lp, toks = r.get("lp") or [], r.get("lp_tok") or []
    if not lp:
        return None
    a = sum(lp) / len(lp)
    text = "".join(toks); code = (r.get("code") or "").strip()
    i = text.rfind(code) if code else -1
    if i < 0:
        return {"a": a, "b": a, "c": min(lp)}
    j, pos, sel = i + len(code), 0, []
    for t, l in zip(toks, lp):
        if pos + len(t) > i and pos < j:
            sel.append(l)
        pos += len(t)
    return {"a": a, "b": sum(sel) / len(sel), "c": min(sel)}


def auroc(pos, neg):   # P(score of a correct program > score of a wrong one), ties count 1/2
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks, i = {}, 0
    rs = [0.0] * len(allv)
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        for k in range(i, j + 1):
            rs[k] = (i + j) / 2 + 1
        i = j + 1
    rpos = sum(r for r, (_, y) in zip(rs, allv) if y)
    return (rpos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def load(cond):
    R = {}
    for sd in SEEDS:
        p = f"{RES}/geocross_S2_C1_geox{M}_{cond}_t07s{sd}.jsonl"
        if os.path.exists(p):
            for r in map(json.loads, open(p)):
                s = scores(r)
                if s is not None:
                    R[(r["task"], r["n"], r["inst"], sd)] = (r, s)
    return R


def auc_table(R, sc, keys=None):
    by_task = defaultdict(lambda: ([], []))
    for (task, n, inst, sd), (r, s) in R.items():
        if keys is not None and (task, n, inst) not in keys:
            continue
        by_task[task][0 if r["class"] == "correct_all" else 1].append(s[sc])
    per = {t: auroc(p, q) for t, (p, q) in by_task.items()}
    valid = [v for v in per.values() if v is not None]
    pooled = auroc([v for p, _ in by_task.values() for v in p], [v for _, q in by_task.values() for v in q])
    return per, (sum(valid) / len(valid) if valid else None), pooled


def boot(R, sc, B=1000, seed=0):
    inst = sorted({k[:3] for k in R}); rng = random.Random(seed); mac, poo = [], []
    for _ in range(B):
        samp = Counter(rng.choice(inst) for _ in inst)
        Rb = {}
        for k, v in R.items():
            for c in range(samp.get(k[:3], 0)):
                Rb[k + (c,)] = v
        Rb2 = {(k[0], k[1], k[2], (k[3], k[4])): v for k, v in Rb.items()}
        _, m_, p_ = auc_table(Rb2, sc)
        if m_ is not None:
            mac.append(m_)
        if p_ is not None:
            poo.append(p_)
    mac.sort(); poo.sort()
    q = lambda xs: (xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]) if xs else (None, None)
    return q(mac), q(poo)


def select(R, sc):
    groups = defaultdict(dict)
    for (task, n, inst, sd), v in R.items():
        groups[(task, n, inst)][sd] = v

    def one(k):
        g = groups[k]; task, n, inst = k
        rng = random.Random(f"{task}-{n}-{inst}")
        V = variants(task, base_instance(task, n, rng), rng)
        cons = []
        for sd, (r, s) in g.items():
            if r.get("code"):
                base, bad = mr_check(r["code"], task, V)
                if base is not None and not bad:
                    cons.append((sd, base, s[sc]))
        ok = {sd: r["class"] == "correct_all" for sd, (r, s) in g.items()}
        single = sum(ok.values()) / len(ok)
        conf = ok[max(g, key=lambda sd: g[sd][1][sc])]
        if cons:
            vote = Counter(b for _, b, _ in cons).most_common(1)[0][0]
            mr = ok[next(sd for sd, b, _ in cons if b == vote)]
            tot = Counter(); [tot.update({b: c}) for _, b, c in cons]   # hybrid: vote, ties broken by summed confidence
            cnt = Counter(b for _, b, _ in cons); top = max(cnt.values())
            best = max((b for b in cnt if cnt[b] == top), key=lambda b: tot[b])
            hyb = ok[max((x for x in cons if x[1] == best), key=lambda x: x[2])[0]]
        else:
            mr, hyb = False, conf
        return task, single, conf, mr, hyb, any(ok.values()), bool(cons)

    with ThreadPoolExecutor(24) as ex:
        return list(ex.map(one, sorted(k for k in groups if len(groups[k]) == len(SEEDS))))


if __name__ == "__main__":
    for cond in ("dis0", "dis8", "hard"):
        R = load(cond)
        if not R:
            print(f"{cond}: no data"); continue
        acc = sum(r["class"] == "correct_all" for r, _ in R.values())
        print(f"\n=== {M} {cond}: {len(R)} programs ({len({k[3] for k in R})} seeds), correct {acc} ({100 * acc / len(R):.1f}%)")
        for sc in ("a", "b", "c"):
            per, mac, poo = auc_table(R, sc)
            (ml, mh), (pl, ph) = boot(R, sc, B=300 if sc != "a" else 1000)
            print(f"  score {sc}: macro AUROC {mac:.3f} [{ml:.3f}, {mh:.3f}] | pooled {poo:.3f} [{pl:.3f}, {ph:.3f}] | per task "
                  + ", ".join(f"{t} {v:.2f}" if v is not None else f"{t} n/a" for t, v in sorted(per.items())))
        sel = select(R, "a")
        if sel:
            n = len(sel)
            tot = lambda i: sum(x[i] for x in sel)
            print(f"  selection over {len(SEEDS)} samples, {n} instances: single {100 * tot(1) / n:.1f} | max-conf {100 * tot(2) / n:.1f} | "
                  f"MR-select {100 * tot(3) / n:.1f} | hybrid {100 * tot(4) / n:.1f} | oracle-any {100 * tot(5) / n:.1f} | "
                  f"no MR-consistent candidate {n - tot(6)}")
            for t in sorted({x[0] for x in sel}):
                xs = [x for x in sel if x[0] == t]; m = len(xs)
                print(f"    {t:9s} single {100 * sum(x[1] for x in xs) / m:5.1f} | conf {100 * sum(x[2] for x in xs) / m:5.1f} | "
                      f"MR {100 * sum(x[3] for x in xs) / m:5.1f} | hybrid {100 * sum(x[4] for x in xs) / m:5.1f} | oracle {100 * sum(x[5] for x in xs) / m:5.1f}")
