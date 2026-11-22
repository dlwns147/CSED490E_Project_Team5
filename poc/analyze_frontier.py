"""Course metric for the word-problem method (CRITIQUE PLAN P1, 2026-11-20): utility = 100 * right - rate * thousand tokens, at several
exchange rates and under three cost views, for the full method and every stored baseline, paired by (problem, seed).

Arms (per answering model m, peer = the other model of the pair Qwen3-8B / gpt-oss-20b):
  OWN     the model's own program (formx; mipf on optnew)                      cost: its tokens
  THINK   the stored thinking program (thinkf on MAMO / NL4OPT+IndustryOR, thinkfree on the other held-out sets)
  CASC    peer cascade (XPEER): own program accepted when the peer's own program prints the same value, else THINK
  T>OWN   typed menu; a valid and grounded reading goes to the fixed solver, else OWN        cost: typed call + fallback
  T>CASC  typed menu, else CASC (the full method)
Cost views: "out" = output tokens; "size" = output tokens x active parameters / 8B (Qwen3-8B 8, gpt-oss-20b 3.6, SIRL-7B 7, ...);
"in+out" = output + 0.25 x estimated input (each call re-reads the question: chars/4 + 250 tokens of instructions; repair rounds of the
baselines re-send their history, approximated by rounds x (question + 250 + 600)).
Template block: the MAMO ComplexLP max-flow / TSP / facility problems, where the related-work baselines ran (results/x3/orbase_*).

usage: [OR_CLEAN=1] python3 poc/analyze_frontier.py [--boot 2000] [--nopool]   (OR_CLEAN=1: expert-audited problems only)      (reads results/x3 and $POC_DATA, default ../nlp_data; prints tables)
"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X3 = f"{ROOT}/results/x3"
D = os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data"))
BOOT = int(sys.argv[sys.argv.index("--boot") + 1]) if "--boot" in sys.argv else 2000
RATES = (0.25, 0.5, 1.0, 2.0)
ACTIVE = {"q8b": 8.0, "oss20": 3.6, "oss120": 5.1, "q32": 32.0, "sirl": 7.0}
PEER = {"q8b": "oss20", "oss20": "q8b"}
SEEDS = (1, 2, 3)
NOPOOL = "--nopool" in sys.argv   # 11-20: formx's prompt carries a program for the most similar OTHER problem of the same benchmark, from a
# pool built by running five models twice over the whole benchmark (run_form.py); that pool's tokens are not in any arm's cost and the
# related-work baselines did not get it. --nopool uses the own programs without the pool (mipf: API card; freef: library card).


def correct(pred, gold):
    if pred is None or gold is None:
        return False
    gold = str(gold)
    if gold.lower().startswith("no best"):
        return pred == "NBS"
    if pred == "NBS":
        return False
    try:
        return abs(float(pred) - float(gold)) <= max(1e-2, 1e-3 * abs(float(gold)))
    except (TypeError, ValueError):
        return False


def agree(a, b):
    """two programs print the same value (the project tolerance, relative to the second)"""
    if a is None or b is None:
        return False
    if "NBS" in (a, b):
        return a == b
    try:
        return abs(float(a) - float(b)) <= max(1e-2, 1e-3 * abs(float(b)))
    except (TypeError, ValueError):
        return False


def valid(t):
    d = t["data"] or {}; ty = t["type"]
    if t["pred"] is None:
        return False
    if ty == "max_flow":
        nodes = {str(a) for a, _, _ in d.get("edges", [])} | {str(b) for _, b, _ in d.get("edges", [])}
        return str(d.get("source")) in nodes and str(d.get("sink")) in nodes and str(d.get("source")) != str(d.get("sink")) and t["pred"] > 0
    if ty == "facility_location":
        cust = {str(c) for _, c, _ in d.get("ship_cost", [])}; fac = {str(f) for f, _, _ in d.get("ship_cost", [])}
        return bool(d.get("demand")) and {str(c) for c in d["demand"]} <= cust and {str(f) for f in d.get("open_cost", {})} <= fac
    return ty == "tsp"


def grounded(t, q):
    d = t["data"] or {}; ql = q.lower(); toks = set(re.findall(r"[a-z0-9]+", ql))
    N = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", q.replace(",", ""))}
    ok = lambda lab: (s in toks) if re.fullmatch(r"\d+", s := str(lab).lower().replace("_", " ").strip()) else (s in ql)
    try:
        if t["type"] in ("max_flow", "tsp"):
            labs = [a for a, _, _ in d["edges"]] + [b for _, b, _ in d["edges"]] + ([d.get("source"), d.get("sink")] if t["type"] == "max_flow" else [])
            vals = [c for _, _, c in d["edges"]]
        else:
            labs = list(d["open_cost"]) + list(d["capacity"]) + list(d["demand"]) + [a for a, _, _ in d["ship_cost"]] + [b for _, b, _ in d["ship_cost"]]
            vals = list(d["open_cost"].values()) + list(d["capacity"].values()) + list(d["demand"].values()) + [c for _, _, c in d["ship_cost"]]
        return all(ok(x) for x in labs) and all(float(v) in N or float(v) == 0 for v in vals)
    except (TypeError, ValueError, KeyError):
        return False


def questions():
    Q = {}
    for name, fn in (("mamo_easy", "MAMO_EasyLP"), ("mamo_complex", "MAMO_ComplexLP")):
        for k, l in enumerate(l for l in open(f"{D}/MAMO/{fn}.json") if l.strip()):
            Q[f"{name}-{k}"] = json.loads(l)["en_question"]
    for name in ("nl4opt", "industryor"):
        for k, r in enumerate(json.load(open(f"{X3}/{name}.json"))):
            Q[f"{name}-{k}"] = r["en_question"]
    for k, l in enumerate(open(f"{D}/storm/STORM/data/test.tir_prompt.OptMath.jsonl")):
        Q[f"optmath-{k}"] = json.loads(l)["prompt"].split("### Problem:\n", 1)[1]
    for r in json.load(open(f"{D}/optibench/ReSocratic/data/OptiBench.json")):
        Q[f"optibench-{r['index']}"] = r["question"]
    for r in map(json.loads, open(f"{D}/bwor/test.jsonl")):
        Q[f"bwor-{r['id']}"] = r["en_question"]
    for r in map(json.loads, open(f"{D}/logior/logior.jsonl")):
        Q[f"logior-{r['prob_id']}"] = r["description"]
    for k, l in enumerate(open(f"{D}/sirl_fixed/OptMATH_Bench_193.jsonl")):
        Q[f"optnew-{k}"] = json.loads(l)["en_question"].strip()
    if os.path.exists(f"{D}/optmath_train/omtf_items.jsonl"):   # C-0 (PREREG_FRESH, 2026-11-22): 300 fresh OptMATH-Train problems
        for r in map(json.loads, open(f"{D}/optmath_train/omtf_items.jsonl")):
            Q[r["id"]] = r["q"]
    return Q


Q = questions()
norm = lambda q: re.sub(r"\s+", " ", q).strip()
FIX = {norm(r["en_question"]): str(r["en_answer"]).strip() for r in map(json.loads, open(f"{D}/sirl_fixed/MAMO_ComplexLP_fixed.jsonl"))}


def gold_of(i, g):
    if i.startswith("mamo_complex"):   # SIRL's corrected ComplexLP labels; problems without one are dropped
        v = FIX.get(norm(Q[i]))
        return v if v not in (None, "", "None") else None
    return g


def setof(i):
    h = i.split("-", 1)[0]
    return "x3" if h in ("nl4opt", "industryor") else h


CLEAN = None
if os.environ.get("OR_CLEAN") == "1":   # expert-audited subsets only (Xiao et al. 2025; poc/or_clean.py): MAMO, OptiBench, NL4OPT
    _d = json.load(open(f"{D}/clean_or/clean_ids.json")); CLEAN = (set(_d["sets"]), set(_d["keep"]))


def load(path, sets=None):
    out = {}
    for s in SEEDS:
        f = path.format(s=s)
        if os.path.exists(f):
            for r in map(json.loads, open(f)):
                if CLEAN and r["id"].rsplit("-", 1)[0] in CLEAN[0] and r["id"] not in CLEAN[1]:
                    continue
                if sets is None or setof(r["id"]) in sets:
                    out[(r["id"], s)] = r
    return out


SETS = ("mamo_complex", "mamo_easy", "x3", "optmath", "optibench", "bwor", "logior", "optnew")


def files(m, st):
    """typed, own, think file patterns for model m on set st"""
    if NOPOOL and st != "optnew":
        own = {"mamo_complex": "mamo_mipf", "mamo_easy": "mamo_mipf", "x3": "mipf", "optmath": "optmath_mipf"}.get(st, f"{st}_freef")
        t, _, k = files.__wrapped__(m, st)
        return t, f"{X3}/opt_{m}_{own}_s{{s}}.jsonl", k
    return files.__wrapped__(m, st)


def _files(m, st):
    if st.startswith("mamo"):
        return f"{X3}/typed_{m}all_s{{s}}.jsonl", f"{X3}/opt_{m}_mamo_formx_s{{s}}.jsonl", f"{X3}/opt_{m}_mamo_thinkf_s{{s}}.jsonl"
    if st == "optnew":
        return f"{X3}/typed_{m}new_s{{s}}.jsonl", f"{X3}/opt_{m}_optnew_mipf_s{{s}}.jsonl", None
    if st == "omtf":
        return f"{X3}/typed_{m}omtf_s{{s}}.jsonl", f"{X3}/opt_{m}_omtf_freef_s{{s}}.jsonl", f"{X3}/opt_{m}_omtf_thinkfree_s{{s}}.jsonl"
    if st == "x3":
        return f"{X3}/typed_{m}ho_s{{s}}.jsonl", f"{X3}/opt_{m}_formx_s{{s}}.jsonl", f"{X3}/opt_{m}_thinkf_s{{s}}.jsonl"
    return f"{X3}/typed_{m}ho_s{{s}}.jsonl", f"{X3}/opt_{m}_{st}_formx_s{{s}}.jsonl", f"{X3}/opt_{m}_{st}_thinkfree_s{{s}}.jsonl"


files.__wrapped__ = _files
qtok = lambda i: len(Q[i]) / 4 + 250


def items(m, st):
    """per (problem, seed): {arm: (right, out_tokens, size_tokens, input_tokens)}"""
    ft, fo, fk = files(m, st)
    p = PEER[m]; fpo = files(p, st)[1]
    T, O, P = load(ft, {st}), load(fo, {st}), load(fpo, {st})
    K = load(fk, {st}) if fk else {}
    K0 = K
    if os.environ.get("SOL2_ADJ") and fk:   # PREREG_ADJ: escalated problem-seeds think with the two disagreeing programs as evidence
        tg = {"x3": f"{m}_x3"}.get(st, f"{m}_{st}")
        A = load(f"{X3}/opt_{tg}_thinkadj_s{{s}}.jsonl", {st})
        K = {**K, **A}
    RP = {}
    if NOPOOL and not st.startswith("mamo"):   # PREREG_TYPED addendum J: the recipe's repair turn on the pool-free own program
        arm = "freef" if st in ("optibench", "bwor", "logior", "omtf") else "mipf"
        RP = load(f"{X3}/repair_{m}_{st}_{arm}_s{{s}}.jsonl", {st})
    w, wp = ACTIVE[m] / 8, ACTIVE[p] / 8
    RETRY = {"S": K0, "X": load(files(p, st)[2], {st})} if (RP and fk) else None
    rows = []
    for k in sorted(set(T) & set(O)):
        i = k[0]; g = gold_of(i, O[k]["gold"])
        if g is None:
            continue
        t, o = T[k], O[k]
        a = {}
        ot = o["out_tokens"]
        a["OWN"] = (correct(o["pred"], g), ot, ot * w, qtok(i))
        if k in K:
            th = K[k]["out_tokens"]
            a["THINK"] = (correct(K[k]["pred"], g), th, th * w, qtok(i))
            if k in P:
                acc = o["pred"] is not None and agree(o["pred"], P[k]["pred"])
                pt = P[k]["out_tokens"]
                ok = correct(o["pred"], g) if acc else correct(K[k]["pred"], g)
                tok = ot + pt + (0 if acc else th)
                a["CASC"] = (ok, tok, ot * w + pt * wp + (0 if acc else th * w), qtok(i) * (2 if acc else 3))
                if RP:   # CASCR: own program; on a visible failure one repair (its tokens paid); then peer agreement; else thinking
                    vis = o.get("status") != "ok" or o["pred"] in (None, "NBS")
                    r = RP.get(k) if vis else None
                    q, rt = (r["pred"], r.get("out_tokens") or 0) if r else (o["pred"], 0)
                    acc = q is not None and q != "NBS" and agree(q, P[k]["pred"])
                    ok = correct(q, g) if acc else correct(K[k]["pred"], g)
                    a["CASCR"] = (ok, ot + rt + pt + (0 if acc else th), (ot + rt) * w + pt * wp + (0 if acc else th * w),
                                  qtok(i) * (2 + bool(r) + (0 if acc else 1)))
                    if RETRY:
                        a["CASCR+RS"] = a["CASCR+RX"] = a["CASCR"]
                    if not acc and RETRY:   # PREREG_ESCT: on a visibly failed think, retry with the same model (RS) or the other family (RX)
                        tf = K[k].get("status") != "ok" or K[k]["pred"] in (None, "NBS")
                        base = a["CASCR"]
                        for nm, src, ww in (("CASCR+RS", RETRY["S"].get((k[0], k[1] % 3 + 1)), w), ("CASCR+RX", RETRY["X"].get(k), wp)):
                            if tf and src is not None:
                                st_ = src["out_tokens"]
                                a[nm] = (correct(src["pred"], g), base[1] + st_, base[2] + st_ * ww, base[3] + qtok(i))
                            else:
                                a[nm] = base
        routed = t["type"] in ("max_flow", "tsp", "facility_location") and valid(t) and grounded(t, Q[i])
        tt = t["tokens"]
        for base, name in (("OWN", "T>OWN"), ("CASC", "T>CASC"), ("CASCR", "T>CASCR"), ("CASCR+RS", "T>CASCR+RS"), ("CASCR+RX", "T>CASCR+RX")):
            if base in a:
                b = a[base]
                a[name] = (correct(t["pred"], g), tt, tt * w, qtok(i)) if routed else (b[0], tt + b[1], tt * w + b[2], qtok(i) + b[3])
        rows.append((k, routed, a))
    return rows


def util(x, rate, view):
    ok, out, size, inp = x
    cost = {"out": out, "size": size, "in+out": out + 0.25 * inp}[view]
    return 100 * ok - rate * cost / 1000


def ci(d):
    import numpy as np
    d = np.asarray(d, float); rng = np.random.default_rng(0)
    bs = np.sort(d[rng.integers(0, len(d), (BOOT, len(d)))].mean(1))
    return d.mean(), bs[int(0.025 * BOOT)], bs[int(0.975 * BOOT) - 1]


def table(m, rows, label):
    arms = [x for x in ("T>CASCR", "T>CASC", "T>OWN", "CASCR", "CASC", "OWN", "THINK") if all(x in a for _, _, a in rows)]
    n = len(rows)
    print(f"\n== {m} {label}: n = {n} (problem x seed), routed to a fixed solver {sum(r for _, r, _ in rows)}")
    print(f"   {'arm':7s} {'acc':>6s} {'ktok':>6s} | U(0.5) | method - arm, U at rate 0.5 [95% CI] | sign at rates {RATES} (out / size / in+out)")
    top = arms[0]
    for x in arms:
        acc = 100 * sum(a[x][0] for _, _, a in rows) / n; kt = sum(a[x][1] for _, _, a in rows) / n / 1000
        u = sum(util(a[x], 0.5, "out") for _, _, a in rows) / n
        line = f"   {x:7s} {acc:6.1f} {kt:6.2f} | {u:6.1f}"
        if x != top:
            mu, lo, hi = ci([util(a[top], 0.5, "out") - util(a[x], 0.5, "out") for _, _, a in rows])
            sg = " / ".join("".join("+" if sum(util(a[top], r, v) - util(a[x], r, v) for _, _, a in rows) > 0 else "-" for r in RATES)
                            for v in ("out", "size", "in+out"))
            line += f" | {top} - {x}: {mu:+5.1f} [{lo:+5.1f}, {hi:+5.1f}] | {sg}"
        print(line)


def main():
    for m in ("q8b", "oss20"):
        pooled = []
        for st in SETS:
            rows = items(m, st)
            if rows:
                table(m, rows, st)
                if st not in ("mamo_complex", "mamo_easy"):
                    pooled += rows
        table(m, [r for r in pooled if all(x in r[2] for x in ("CASC", "THINK"))], "held-out pooled (x3 + optmath + optibench + bwor + logior)")
    template_block()


def template_block():
    """ComplexLP template problems: the full method vs the related-work baselines run in our harness (with the API card)."""
    print("\n== Template problems (MAMO ComplexLP max flow / TSP / facility; SIRL-corrected labels): full method vs related-work baselines")
    print("   rows: problem x seed with every arm present; baselines' input tokens approximate rounds x (question + 850)")
    for m, tags in (("q8b", ("q8bc", "q8bf")), ("oss20", ("oss20c", "oss20f"))):
        full = {k: a for k, _, a in items(m, "mamo_complex") if "T>CASC" in a}
        w = ACTIVE[m] / 8
        arms = defaultdict(dict)
        for tag in tags:
            for arm in ("selfdebug", "optimus", "fiveel", "coe", "fewshot"):
                for k, r in load(f"{X3}/orbase_{tag}_{arm}_s{{s}}.jsonl").items():
                    g = gold_of(k[0], r["gold"])
                    if g is not None:
                        nr = len(r.get("rounds") or [1])
                        arms[arm][k] = (correct(_num(r["pred"]), g), r["tokens"], r["tokens"] * w, nr * (len(Q[k[0]]) / 4 + 850))
        for k, r in load(f"{X3}/orbase_sirl3_sirl_s{{s}}.jsonl").items():
            g = gold_of(k[0], r["gold"])
            if g is not None:
                arms["SIRL-7B"][k] = (correct(_num(r["pred"]), g), r["tokens"], r["tokens"] * ACTIVE["sirl"] / 8, qtok(k[0]))
        for arm, R in arms.items():
            ks = [k for k in R if k in full]
            if not ks:
                continue
            n = len(ks)
            acc = lambda f: 100 * sum(f(k)[0] for k in ks) / n
            mu, lo, hi = ci([util(full[k]["T>CASC"], 0.5, "out") - util(R[k], 0.5, "out") for k in ks])
            sg = " / ".join("".join("+" if sum(util(full[k]["T>CASC"], r, v) - util(R[k], r, v) for k in ks) > 0 else "-" for r in RATES)
                            for v in ("out", "size", "in+out"))
            print(f"   {m:5s} {arm:9s} n={n:3d} full {acc(lambda k: full[k]['T>CASC']):5.1f}% @ {sum(full[k]['T>CASC'][1] for k in ks)/n/1000:5.2f}k"
                  f"  baseline {acc(lambda k: R[k]):5.1f}% @ {sum(R[k][1] for k in ks)/n/1000:5.2f}k | U diff {mu:+5.1f} [{lo:+5.1f}, {hi:+5.1f}] | {sg}")


def _num(p):
    if p in (None, "NBS"):
        return p
    try:
        return float(p)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
