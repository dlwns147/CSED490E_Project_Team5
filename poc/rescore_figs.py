"""Numbers behind the helper-related figures (figs/fig2, fig4, fig6, fig7, fig8), raw and packaging-free, plus an audit of the other
hard-coded numbers in poc/make_figures.py (fig1, fig3, fig5). CPU only, no model calls.

Packaging-free = the logic of poc/rescore_prelude.py: every stored program whose class is "crash" is re-run on all 8 metamorphic variants
with the helpers that were OFFERED in its prompt PRE-DEFINED in front of it; the model's own definitions come later and override. A program
that only crashed because it called a helper without copying it is then scored on its logic. All other rows keep their stored class.
(rescore_prelude.py runs at import, so its rescore() is copied here.) The prelude per arm:
  related / unrelated  --distract K runs: needed helpers + the K distractors (geo_distractors.toolbox, same RNG key as run_geo_cross.py)
  prims                the task-matched "pt" arm (--primitives --prims_task): the task's needed predicates (run_geo_cross.prims)
  None                 runs that offer no helpers (stored classes are used as they are)

MR-select (fig6, fig8) = poc/mr_select.py: per instance, run each of the 3 seeds' programs on the metamorphic copies of the given instance, keep
the consistent ones, majority-vote the identity output, pick the first program with it, score the pick (no consistent program = abstain,
counted wrong). Packaging-free version: candidates
run with the prelude, the pick is scored packaging-free.

Extra diagnostics per run (not used for the plotted numbers):
  copy_nameerr  crash rows whose identity run (no prelude) raises NameError on a helper that was offered (= copy failures)
  pf_all        correct count if EVERY non-correct row (not only crashes) is re-run with the prelude: catches copy failures that only
                fire on a non-identity variant (they show up as degen_only / transform_only instead of crash)
  dis_mismatch  rows whose stored "distractors" field differs from the reconstructed toolbox (must be 0, otherwise the prelude is wrong)

Deltas pair K0 and K8 rows by (seed, task, n, inst); 95% CI = cluster bootstrap over instances (task, n, inst), seeds of the same
instance resampled together, 10,000 resamples, numpy default_rng(0) per comparison.

usage: rescore_figs.py [--workers 32]      writes results/figs_packaging_free.json and prints the tables"""
import argparse, json, os, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import toolbox  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_cross import classify, prims  # noqa: E402
from run_geo_mr import MR, expected_rel, run_out  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
OUT = f"{RES}/figs_packaging_free.json"
NB, SEED = 10_000, 0
Q = ("8b", "14b", "32b")
QNAME = {"8b": "Qwen3-8B", "14b": "Qwen3-14B", "32b": "Qwen3-32B"}
S = lambda fmt, seeds: [fmt.format(s=s) for s in seeds]

# ---- sources -----------------------------------------------------------------------------------------------------------------------
# fig2: S4d dose-response (poc/queue_distract.sh): "should use" header, no --stdlib, n_inst 10 (100 programs), T=0.7, seeds 1-2
FIG2 = {m: {**{str(k): ([f"geox{m}_dis{k}_t07s{s}" for s in (1, 2)], k, "related") for k in (0, 2, 4, 8)},
            "U": ([f"geox{m}_disU8_t07s{s}" for s in (1, 2)], 8, "unrelated")}   # --distract 8 unrelated = the whole pool of 6
        for m in Q}

# fig7 (and fig4's geometry half): K0 vs K8 related helpers, "should use" header, --stdlib, T=0.7 (R1: 0.6); seeds in the same order
# for K0 and K8. Every row is plotted packaging-free.
FIG7 = [  # label, mode (0 standard / 1 reasoning), K0 tags, K8 tags, source queue
    ("Qwen3-1.7B", 0, ["X_geox1_7b_dis0_t07s1"], ["X_geox1_7b_dis8_t07s1"], "queue_q17dis.sh"),
    ("Llama-3.1-8B", 0, S("X_geoxllama8_dis0_t07s{s}", (1, 2)), S("X_geoxllama8_dis8_t07s{s}", (1, 2)), "queue_l8dis.sh"),
    ("Qwen3-8B", 0, ["F_geox8b_dis0_t07s1"], ["F_geox8b_dis8_t07s1"], "queue_prelude.sh (K0) / queue_final_geo.sh (K8)"),
    ("Qwen3-14B", 0, ["F_geox14b_dis0_t07s1"], ["F_geox14b_dis8_t07s1"], "queue_prelude.sh (K0) / queue_final_geo.sh (K8)"),
    ("Qwen3-32B", 0, ["F_geox32b_dis0_t07s1"], ["F_geox32b_dis8_t07s1"], "queue_prelude.sh (K0) / queue_final_geo.sh (K8)"),
    ("Llama-3.3-70B", 0, S("X_geoxllama70_dis0_t07s{s}", (1, 2, 3)), S("X_geoxllama70_dis8_t07s{s}", (1, 2, 3)), "queue_llama*"),
    ("Qwen3-1.7B, thinking", 1, S("T_geox1_7b_dis0_s{s}", (1, 2, 3)), S("T_geox1_7b_dis8_s{s}", (1, 2, 3)), "queue_q17dis.sh / queue_q17think.sh"),
    ("Qwen3-8B, thinking", 1, S("T_geox8b_dis0_s{s}", (1, 2)), S("T_geox8b_dis8_s{s}", (1, 2)), "queue_thinkdis2.sh"),
    ("Qwen3-14B, thinking", 1, ["T_geox14b_dis0", "T_geox14b_dis0_s2"], ["T_geox14b_dis8", "T_geox14b_dis8_s2"], "queue_thinkdis.sh / 2"),
    ("Qwen3-32B, thinking", 1, ["T_geox32b_dis0", "T_geox32b_dis0_s2"], ["T_geox32b_dis8", "T_geox32b_dis8_s2"], "queue_thinkdis.sh / 2"),
    ("R1-Distill-Llama-70B", 1, ["X_geoxr1l70_dis0_t06s1"], ["X_geoxr1l70_dis8_t06s1"], "queue_llama*"),
    ("gpt-oss-20b, low", 1, ["O5_geoxoss20low_k0", "O5_geoxoss20low_k0_s2"], ["O5_geoxoss20low_k8", "O5_geoxoss20low_k8_s2"], "queue_oss.sh / queue_oss20s2.sh"),
    ("gpt-oss-20b, medium", 1, ["O5_geoxoss20med_k0", "O5_geoxoss20med_k0_s2"], ["O5_geoxoss20med_k8", "O5_geoxoss20med_k8_s2"], "queue_oss.sh / queue_oss20s2.sh"),
    ("gpt-oss-120b, low", 1, ["O5_geoxoss120low_k0"], ["O5_geoxoss120low_k8fix2"], "queue_oss.sh (K0) / queue_ossfix2.sh (K8, fixed extractor)"),
    ("gpt-oss-120b, medium", 1, ["O5_geoxoss120med_k0"], ["O5_geoxoss120med_k8fix2"], "queue_oss.sh (K0) / queue_ossfix2.sh (K8, fixed extractor)"),
]
OSS_HIGH = [("gpt-oss-20b, high (24k cap)", ["O5_geoxoss20hig_k0"], ["O5_geoxoss20hig_k8"]),
            ("gpt-oss-120b, high (24k cap)", ["O5_geoxoss120hig_k0"], ["O5_geoxoss120hig_k8"])]
PER_TASK = ["Qwen3-1.7B"]   # rows whose per-task K0 -> K8 counts are reported (the pooled delta hides opposite task effects)

# fig6 / fig8 (FINAL geometry runs, --stdlib, n = 300 per seed, T=0.7): conditions -> (tags, K, kind) or ("MR", tags, K, kind)
SINGLE = lambda tags, K, kind: ("runs", tags, K, kind)
MRSEL = lambda tags, K, kind: ("mr", tags, K, kind)
FIG6 = {m: {"one tool-free sample (mean of 3)": SINGLE(S(f"F_geox{m}_base_t07s{{s}}", (1, 2, 3)), 0, None),
            "one sample with hand-picked helpers (task-matched predicates)": SINGLE([f"F_geox{m}_pt_t07s1"], 0, "prims"),
            "3 tool-free samples + metamorphic check": MRSEL(S(f"F_geox{m}_base_t07s{{s}}", (1, 2, 3)), 0, None)} for m in Q}
T8 = {"8b": S("T_geox8b_dis8_s{s}", (1, 2)), "14b": ["T_geox14b_dis8", "T_geox14b_dis8_s2"], "32b": ["T_geox32b_dis8", "T_geox32b_dis8_s2"]}
FIG8 = {m: {"8 extra helpers, one sample (mean of 3)": SINGLE(S(f"F_geox{m}_dis8_t07s{{s}}", (1, 2, 3)), 8, "related"),
            "8 extra helpers, 3 samples + check": MRSEL(S(f"F_geox{m}_dis8_t07s{{s}}", (1, 2, 3)), 8, "related"),
            "needed helpers only, same header (K = 0), one sample": SINGLE([f"F_geox{m}_dis0_t07s1"], 0, "related"),
            "needed helpers only, task-matched predicates header, one sample": SINGLE([f"F_geox{m}_pt_t07s1"], 0, "prims"),
            "8 extra helpers, thinking (2 seeds, n = 100 each)": SINGLE(T8[m], 8, "related")} for m in Q}
# audit only (raw; no helpers offered or packaging is the point of the figure)
REF = [("fig3 prelude-header runs: Qwen3-{m} K0 -> K8 (helpers pre-defined at generation)", "F_geox{m}_dis0pre_t07s1", "F_geox{m}_dis8pre_t07s1"),
       ("old fig4/fig7: Qwen3-{m} task-matched predicates -> K8 (wrong baseline)", "F_geox{m}_pt_t07s1", "F_geox{m}_dis8_t07s1")]
FIG1 = [("Llama-3.1-8B, greedy, with the stdlib sentence", "geoxllama8b_std_v2"), ("Qwen3-14B, greedy, with the stdlib sentence", "geox14b_std")]


def load(tag):
    return [json.loads(l) for l in open(f"{RES}/geocross_{tag}.jsonl")]


def prelude(task, n, inst, K, kind):
    """(code to pre-define, distractor names, all offered helper names)"""
    if kind == "prims":
        tb, dis = prims(task, SimpleNamespace(prims_task=True)), []
    else:
        tb, dis = toolbox(task, K, kind, random.Random(f"{task}-{n}-{inst}-tb"))
    return "\n".join(re.findall(r"```python\n(.*?)```", tb, re.S)) + "\n", dis, re.findall(r"^def (\w+)\(", tb, re.M)


def instance_variants(task, n, inst):
    rng = random.Random(f"{task}-{n}-{inst}")
    return variants(task, base_instance(task, n, rng), rng)


def run_variants(task, n, inst, code):
    """same execution/scoring as run_geo_cross.py / rescore_prelude.py. The identity variant runs first: if it fails, classify() returns
    crash / logic from it alone, so the other 7 variants are only executed when identity is correct (same class, ~8x less CPU)."""
    V = instance_variants(task, n, inst)
    res = {}
    for vn in ["identity"] + [v for v in V if v != "identity"]:
        x = V[vn]
        _, stdin, _ = render(task, x)
        o = run_python(code, stdin, timeout=10)
        out = (o.stdout.strip().split() or [None])[-1] if o.status == "ok" else None
        res[vn] = None if out is None and vn == "identity" else (out is not None and out.lower() == answer(task, x))
        if vn == "identity" and not res[vn]:
            return classify({"identity": res[vn]})
    return classify(res)


def rescore(r, K, kind):
    if kind is None:   # no helpers offered: stored classes
        return {"raw": r["class"], "pf": r["class"], "pf_all": r["class"], "copy_nameerr": False, "dis_mismatch": False}
    pre, dis, offered = prelude(r["task"], r["n"], r["inst"], K, kind)
    out = {"raw": r["class"], "pf": r["class"], "pf_all": r["class"], "copy_nameerr": False,
           "dis_mismatch": sorted(dis) != sorted(r.get("distractors") or [])}
    if r["class"] == "correct_all" or not r.get("code"):
        return out
    new = run_variants(r["task"], r["n"], r["inst"], pre + r["code"])
    out["pf_all"] = new
    if r["class"] == "crash":
        out["pf"] = new
        _, stdin, _ = render(r["task"], instance_variants(r["task"], r["n"], r["inst"])["identity"])
        o = run_python(r["code"], stdin, timeout=10)
        m = re.search(r"NameError: name '(\w+)' is not defined", o.stderr or "")
        out["copy_nameerr"] = bool(m and m.group(1) in offered)
    return out


def score_all(specs, workers):
    """specs: list of (tag, K, kind). All rows of all runs go into one pool (no per-run barrier behind slow timeouts)."""
    rows = {sp: load(sp[0]) for sp in specs}
    jobs = [(sp, i) for sp in specs for i in range(len(rows[sp]))]
    jobs.sort(key=lambda j: (j[0][2] is None, rows[j[0]][j[1]]["class"] != "crash"))   # slowest (re-run crashes) first
    sc = {sp: [None] * len(rows[sp]) for sp in specs}
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(rescore, rows[sp][i], sp[1], sp[2]): (sp, i) for sp, i in jobs}
        for done, f in enumerate(as_completed(futs), 1):
            sp, i = futs[f]; sc[sp][i] = f.result()
            if done % 4000 == 0 or done == len(futs):
                print(f"  rescored {done}/{len(futs)} rows", file=sys.stderr, flush=True)
    return {sp: summarize(sp, rows[sp], sc[sp]) for sp in specs}


def summarize(sp, rows, sc):
    tag, K, kind = sp
    keyed = {(r["task"], r["n"], r["inst"]): dict(s, task=r["task"]) for r, s in zip(rows, sc)}
    c = lambda f: sum(s[f] == "correct_all" for s in sc)
    return {"tag": tag, "K": K, "kind": kind, "n": len(rows), "raw_correct": c("raw"), "pf_correct": c("pf"), "pf_all_correct": c("pf_all"),
            "crashes": sum(s["raw"] == "crash" for s in sc), "crashes_pf": sum(s["pf"] == "crash" for s in sc),
            "copy_nameerr": sum(s["copy_nameerr"] for s in sc), "dis_mismatch": sum(s["dis_mismatch"] for s in sc),
            "pf_rescued": dict(Counter(s["pf"] for s in sc if s["raw"] == "crash" and s["pf"] != "crash"))}, keyed


def paired(k0, k8, field):
    """k0/k8: lists (one per seed) of {(task,n,inst): scores}. Returns delta [CI] in points + K0/K8 percentages."""
    inst = sorted(set.intersection(*[set(d) for d in k0 + k8]))
    ok = lambda d, i: float(d[i][field] == "correct_all")
    d = np.array([np.mean([ok(b, i) - ok(a, i) for a, b in zip(k0, k8)]) for i in inst]) * 100
    rng = np.random.default_rng(SEED)
    bs = d[rng.integers(0, len(d), (NB, len(d)))].mean(axis=1)
    p0 = 100 * np.mean([ok(a, i) for a in k0 for i in inst]); p8 = 100 * np.mean([ok(b, i) for b in k8 for i in inst])
    return {"delta": round(float(d.mean()), 2), "lo": round(float(np.percentile(bs, 2.5)), 2), "hi": round(float(np.percentile(bs, 97.5)), 2),
            "k0_pct": round(float(p0), 2), "k8_pct": round(float(p8), 2), "n_instances": len(inst), "n_pairs": len(inst) * len(k0)}


def mr_select(tags, K, kind, cache, ex):
    """mr_select.py over the runs `tags` (one program per seed and instance); returns raw and packaging-free correct counts"""
    rows = {t: {(r["task"], r["n"], r["inst"]): r for r in load(t)} for t in tags}
    keys = sorted(rows[tags[0]])

    def consistent(code, task, V):
        """identity output if the program satisfies every metamorphic relation, else None (= run_geo_mr.mr_check's `base is not None
        and not bad`, stopping at the first violated relation)"""
        base = run_out(code, task, V["identity"])
        for v in MR:
            if base is None:
                return None
            if not (task == "lattice" and v == "scale") and run_out(code, task, V[v]) != expected_rel(task, v, base):
                return None
        return base

    def pick(k, pf):
        V = instance_variants(*k)
        pre = prelude(*k, K, kind)[0] if pf else ""
        cands = []
        for t in tags:
            r = rows[t].get(k)
            if r and r.get("code"):
                base = consistent(pre + r["code"], k[0], V)
                if base is not None:
                    cands.append((t, base))
        if not cands:
            return None
        vote = Counter(b for _, b in cands).most_common(1)[0][0]
        return next(t for t, b in cands if b == vote)

    out = {"tags": tags, "n": len(keys)}
    for field in ("raw", "pf"):
        if not (field == "pf" and kind is None):   # no helpers offered: the packaging-free picks are the raw picks
            picks = list(ex.map(lambda k: pick(k, field == "pf"), keys))
        out[f"{field}_correct"] = sum(cache[(t, K, kind)][1][k][field] == "correct_all" for k, t in zip(keys, picks) if t)
        out[f"{field}_abstain"] = sum(t is None for t in picks)
        out[f"{field}_pct"] = round(100 * out[f"{field}_correct"] / len(keys), 2)
    return out


def co_audit():
    """fig4 optimization half (co_D_*: +8 unneeded OR-Tools lines, 84 instances x 2 seeds) and fig5 (F_co*: 252 instances x 3 seeds).
    No helper functions are offered in CO prompts (extra lines are API documentation), so there is no packaging-free variant."""
    ok = lambda r: bool(r["feasible"] and r["gap"] is not None and r["gap"] <= 1)
    L = lambda t: {r["key"]: r for r in map(json.loads, open(f"{RES}/co_{t}.jsonl"))}
    res = {"fig4_co": {}, "fig5": {}}
    for m in Q:
        a, b = [L(f"D_co{m}_x8_s{s}") for s in (1, 2)], [L(f"D_co{m}_x0_s{s}") for s in (1, 2)]
        keys = sorted(a[0])
        d = np.array([np.mean([ok(x[k]) for x in a]) - np.mean([ok(x[k]) for x in b]) for k in keys]) * 100
        bs = d[np.random.default_rng(SEED).integers(0, len(d), (NB, len(d)))].mean(axis=1)
        res["fig4_co"][QNAME[m]] = {"tags": [f"co_D_co{m}_x{k}_s{s}" for k in (0, 8) for s in (1, 2)], "n_instances": len(keys),
                                    "delta": round(float(d.mean()), 2), "lo": round(float(np.percentile(bs, 2.5)), 2),
                                    "hi": round(float(np.percentile(bs, 97.5)), 2)}
        D = {a_: [L(f"F_co{m}_{a_}_s{s}") for s in (1, 2, 3)] for a_ in ("nodoc", "doc", "doctask")}
        e = {a_: round(float(np.mean([np.mean([ok(r) for r in s.values()]) for s in D[a_]])), 3) for a_ in D}
        best = []
        for k in D["doctask"][0]:
            c = [s[k] for s in D["doctask"] if s[k]["feasible"]]
            b_ = (max(c, key=lambda r: r["value"]) if k.startswith("knapsack") else min(c, key=lambda r: r["value"])) if c else None
            best.append(bool(b_ and ok(b_)))
        e["doctask_best3"] = round(float(np.mean(best)), 3); e["n_instances"] = len(D["nodoc"][0])
        e["scoped_minus_full"] = round(e["doctask"] - e["doc"], 3)
        res["fig5"][QNAME[m]] = e
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=32); a = ap.parse_args()
    ref = [(l.format(m=m), t0.format(m=m), t8.format(m=m)) for l, t0, t8 in REF for m in Q]
    cond_specs = [(t, c[2], c[3]) for F in (FIG6, FIG8) for conds in F.values() for c in conds.values() for t in c[1]]
    specs = list(dict.fromkeys([(t, K, kind) for levels in FIG2.values() for tags, K, kind in levels.values() for t in tags]
                               + [(t, K, "related") for row in FIG7 for K, ts in ((0, row[2]), (8, row[3])) for t in ts]
                               + cond_specs
                               + [(t, K, None) for _, t0, t8 in OSS_HIGH for K, ts in ((0, t0), (8, t8)) for t in ts]
                               + [(t, K, None) for _, t0, t8 in ref for K, t in ((0, t0), (8, t8))]
                               + [(t, 0, None) for _, t in FIG1]))
    cache = score_all(specs, a.workers)
    run = lambda tag, K, kind="related": cache[(tag, K, kind)]
    fmt = lambda p: f"{p['delta']:+.1f} [{p['lo']:+.1f}, {p['hi']:+.1f}]"
    out = {"method": __doc__.split("usage:")[0].strip(), "fig2": {}, "fig7": [], "fig4": {}, "fig6": {}, "fig8": {}, "audit": {}, "gpt_oss_high": []}

    print("== fig2: % correct on all 8 variants, mean of 2 seeds (n = 100 per seed); raw -> packaging-free")
    for m, levels in FIG2.items():
        out["fig2"][QNAME[m]] = {}
        k0 = [run(t, 0)[1] for t in levels["0"][0]]
        line = []
        for lev, (tags, K, kind) in levels.items():
            runs = [run(t, K, kind) for t in tags]
            st = [s for s, _ in runs]; n = sum(s["n"] for s in st)
            e = {"tags": tags, "K": K, "kind": kind, "n": n,
                 "raw_pct": round(100 * sum(s["raw_correct"] for s in st) / n, 2), "pf_pct": round(100 * sum(s["pf_correct"] for s in st) / n, 2),
                 "pf_all_pct": round(100 * sum(s["pf_all_correct"] for s in st) / n, 2), "runs": st}
            if lev != "0":
                e["delta_vs_K0_raw"] = paired(k0, [k for _, k in runs], "raw"); e["delta_vs_K0_pf"] = paired(k0, [k for _, k in runs], "pf")
            out["fig2"][QNAME[m]][lev] = e
            line.append(f"{'K=' + lev if lev != 'U' else 'U6'} {e['raw_pct']:.1f}->{e['pf_pct']:.1f}"
                        f" (crash {sum(s['crashes'] for s in st)}->{sum(s['crashes_pf'] for s in st)}, copyNE {sum(s['copy_nameerr'] for s in st)})")
        print(f"{QNAME[m]:10s} " + " | ".join(line))

    print("\n== fig7: K0 -> K8 related helpers, delta in points [95% CI]; plotted = packaging-free")
    print(f"{'row':24s} {'n':>5s} {'raw K0->K8':>13s} {'raw delta [CI]':>22s} {'pkg-free K0->K8':>16s} {'pkg-free delta [CI]':>22s}  "
          f"crashes K0/K8  copy-NameErr K0/K8  pf_all delta")
    for lab, mode, t0, t8, src in FIG7:
        r0 = [run(t, 0) for t in t0]; r8 = [run(t, 8) for t in t8]
        k0, k8 = [k for _, k in r0], [k for _, k in r8]
        e = {"label": lab, "mode": "reasoning" if mode else "standard", "plotted": "pf", "k0_tags": t0, "k8_tags": t8, "source": src,
             "raw": paired(k0, k8, "raw"), "pf": paired(k0, k8, "pf"), "pf_all": paired(k0, k8, "pf_all"),
             "k0_runs": [s for s, _ in r0], "k8_runs": [s for s, _ in r8]}
        cr = lambda rs, f: sum(s[f] for s, _ in rs)
        e["crashes_k0"], e["crashes_k8"] = cr(r0, "crashes"), cr(r8, "crashes")
        e["copy_nameerr_k0"], e["copy_nameerr_k8"] = cr(r0, "copy_nameerr"), cr(r8, "copy_nameerr")
        e["plot_value"] = [e["pf"]["delta"], e["pf"]["lo"], e["pf"]["hi"]]
        if lab in PER_TASK:   # per-task correct counts (summed over seeds), K0 -> K8
            e["per_task"] = {f: {t: [sum(s[f] == "correct_all" for d in ks for s in d.values() if s["task"] == t) for ks in (k0, k8)]
                                 for t in ("hull", "area2", "pip", "segs", "close")} for f in ("raw", "pf")}
        out["fig7"].append(e)
        R, P = e["raw"], e["pf"]
        print(f"{lab:24s} {R['n_pairs']:5d} {R['k0_pct']:5.1f}->{R['k8_pct']:5.1f}  {fmt(R):>22s} {P['k0_pct']:5.1f}->{P['k8_pct']:5.1f}* {fmt(P):>22s}"
              f"  {e['crashes_k0']:4d}/{e['crashes_k8']:<4d}      {e['copy_nameerr_k0']:4d}/{e['copy_nameerr_k8']:<4d}       {e['pf_all']['delta']:+.1f}")
        if "per_task" in e:
            print(f"{'':24s} per task, correct K0->K8 (pkg-free): " + ", ".join(f"{t} {a_}->{b_}" for t, (a_, b_) in e["per_task"]["pf"].items())
                  + f"  (raw: " + ", ".join(f"{t} {a_}->{b_}" for t, (a_, b_) in e["per_task"]["raw"].items()) + ")")
    for lab, t0, t8 in OSS_HIGH:
        p = paired([run(t, 0, None)[1] for t in t0], [run(t, 8, None)[1] for t in t8], "raw")
        capped = {t: sum(r.get("finish") == "length" for r in load(t)) for t in t0 + t8}
        out["gpt_oss_high"].append({"label": lab, "k0_tags": t0, "k8_tags": t8, "raw": p, "capped_rows": capped})
        print(f"{lab:24s} (not plotted) {p['k0_pct']:5.1f}->{p['k8_pct']:5.1f}  {fmt(p)}  rows that hit the token cap: {capped}")

    print("\n== fig4: geometry K0 -> K8 (packaging-free, = fig7 rows) and optimization +8 unneeded OR-Tools lines (no helpers to copy)")
    co = co_audit()
    out["fig4"] = {"geometry": {e["label"]: {k: e[k] for k in ("k0_tags", "k8_tags", "raw", "pf")} for e in out["fig7"] if e["label"] in QNAME.values()},
                   "optimization": co["fig4_co"]}
    for mn in QNAME.values():
        g, c = out["fig4"]["geometry"][mn], co["fig4_co"][mn]
        print(f"{mn:10s} geometry pkg-free {fmt(g['pf'])} (raw {fmt(g['raw'])}) | optimization {fmt(c)} (n = {c['n_instances']} x 2 seeds)")

    with ThreadPoolExecutor(a.workers) as ex:
        for name, F in (("fig6", FIG6), ("fig8", FIG8)):
            print(f"\n== {name}: % correct on all 8 variants, raw -> packaging-free")
            for m, conds in F.items():
                out[name][QNAME[m]] = {}
                for lab, (how, tags, K, kind) in conds.items():
                    if how == "runs":
                        st = [run(t, K, kind)[0] for t in tags]; n = sum(s["n"] for s in st)
                        e = {"tags": tags, "n": n, "raw_pct": round(100 * sum(s["raw_correct"] for s in st) / n, 2),
                             "pf_pct": round(100 * sum(s["pf_correct"] for s in st) / n, 2), "per_run": [(s["raw_correct"], s["pf_correct"]) for s in st]}
                    else:
                        e = mr_select(tags, K, kind, cache, ex)
                    out[name][QNAME[m]][lab] = e
                    print(f"  {QNAME[m]:10s} {lab:66s} {e['raw_pct']:5.1f} -> {e['pf_pct']:5.1f}   ({', '.join(tags)})")

    print("\n== audit (raw; fig1 offers no helpers, fig3 is the copy-vs-prelude comparison itself, fig5 is CO)")
    out["audit"]["fig1"] = {lab: {"tag": t, "pct": 100 * run(t, 0, None)[0]["raw_correct"] / run(t, 0, None)[0]["n"]} for lab, t in FIG1}
    out["audit"]["fig1_note"] = "the no-stdlib greedy runs (Llama 83, Qwen3-14B 79) have no stored jsonl in results/"
    for lab, v in out["audit"]["fig1"].items():
        print(f"fig1  {lab:50s} {v['pct']:.0f} ({v['tag']})")
    out["audit"]["fig3_copy_in_raw"] = {e["label"]: e["raw"] for e in out["fig7"] if e["label"] in QNAME.values()}
    out["audit"]["reference"] = []
    for lab, t0, t8 in ref:
        p = paired([run(t0, 0, None)[1]], [run(t8, 8, None)[1]], "raw")
        out["audit"]["reference"].append({"label": lab, "k0_tag": t0, "k8_tag": t8, "raw": p})
        print(f"{lab:84s} {p['k0_pct']:5.1f} -> {p['k8_pct']:5.1f}  {fmt(p)}")
    for mn, e in out["audit"]["fig3_copy_in_raw"].items():
        print(f"fig3 copy-in (as measured): {mn:10s} {fmt(e)}")
    out["audit"]["fig5"] = co["fig5"]
    for mn, e in co["fig5"].items():
        print(f"fig5  {mn:10s} no doc {e['nodoc']:.3f} | full sheet {e['doc']:.3f} | snippet {e['doctask']:.3f} (best-of-3 {e['doctask_best3']:.3f})"
              f" | snippet - full {e['scoped_minus_full']:+.3f} | n = {e['n_instances']} x 3 seeds")

    scored = [s for (_, _, kind), (s, _) in cache.items() if kind is not None]
    out["toolbox_mismatch_rows"] = sum(s["dis_mismatch"] for s in scored)
    print(f"\ntoolbox reconstruction mismatches (stored distractors != rebuilt): {out['toolbox_mismatch_rows']} of {sum(s['n'] for s in scored)} rescored rows")
    json.dump(out, open(OUT, "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
