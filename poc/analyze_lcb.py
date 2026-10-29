"""LC-1 (docs/prereg/PREREG_LC.md): policies on LiveCodeBench from run_lcb.py rows and grade_lcb.py grades. Per problem and seed
(tokens = every call's output tokens; the free check = the program passes the problem's sample tests, chk):
  N, T, SB         one non-thinking / thinking / 2k-cut program
  S                self-selective reasoning (Li et al. 2025 style): T if the model said yes, else N (+ the yes / no call)
  N->T             cheap first: N; T where N fails the samples
  N->SB->T         N; SB where N fails the samples; T where SB fails them too
  SB->T->T         the recipe's default (HO-SB): SB; T where SB fails the samples; the next seed's T where T fails them too
  T->T             the check-matched think: T; the next seed's T where T fails the samples
  N->T|hidden      N->T gated on the hidden tests (DART's code gate, which scores with the tests it gates on): T where N is wrong
Accuracy = pass@1 on sample + hidden tests (official grader). Utility = accuracy - 0.5 x ktokens. Paired 95% intervals over problems
(seed means). Also the leak (passes the samples, fails hidden tests) of N / SB / T with how the first hidden test failed, and every
policy by difficulty with its share of the tokens.
LCB_JOIN=1 (sensitivity, not a rule): a threaded program's grade with its threads joined (grade_lcb.py LCB_JOIN) replaces the
official one.
LCB_THINK=thinkh (LC-OSS): gpt-oss's high-effort think (rows thinkh, grade TH) takes T's place in every policy (thinkh64: the same at a 64k cap;
think64: the think at a 64k cap, the LC-1 cap rule).
--pilot (PX, PREREG_MODEL.md): HO-P's k-label pilot over the deployable policies (N->T|hidden out), one cell per model x seed; a tag may
name its think arm (q35g:think64, the LC-1 verdict think).
usage: python analyze_lcb.py [tag[:arm] ...]   (default q8b q14a q35g — Qwen3.5-9B at the general preset, the amendment; LCB_SEEDS=1 for the smoke, where T->T reuses the same seed)"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "lcb")
ITEMS = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "lcb", "lcb_items.jsonl")
POL = ("N", "T", "SB", "S", "N->T", "N->SB->T", "SB->T->T", "T->T", "N->T|hidden")
LAM = 0.5
JOIN = os.environ.get("LCB_JOIN") == "1"
TARM = os.environ.get("LCB_THINK", "think"); TGS = {"think": "T", "thinkh": "TH", "thinkh64": "TH64", "think64": "T64"}; TG = TGS[TARM]
PILOT = "--pilot" in sys.argv
ROWS = {}   # --pilot: (tag, seed) -> one {policy: (right, tokens)} per problem


def pilot(rows, pols, default, reps=1000, ks=(10, 30, 100), alt=None):
    """PX (PREREG_MODEL.md): HO-P's k-label pilot on cells {(model, ..., seed): [{policy: (right, tokens)}]}: the policy with the best
    utility on k random problems of a cell, scored on the whole cell; regret = the cell's best utility - the pick's (1,000 pilots per
    cell). Prints, per lambda, the pilot's mean regret, always using each policy, the best policy per cell and the k = 30 regret by model.
    PX2: on the same draws, the conservative pilot keeps the default unless the policy with the largest mean paired utility gain over it
    beats it by z x SE (one-sided 5%, Bonferroni over the other policies; z = 1.645 as a sensitivity).
    SQL-P7 (alt, PREREG_SQL.md): the label-free token switch — on the same k problems keep the default unless it used more output tokens
    than `alt` there, else `alt` (no labels: tokens and check outcomes only)."""
    import random
    from statistics import NormalDist
    rng = random.Random(0)
    zs = (NormalDist().inv_cdf(1 - 0.05 / (len(pols) - 1)), 1.645)
    U = lambda R, lam: {p: 100 * sum(r[p][0] for r in R) / len(R) - lam * sum(r[p][1] for r in R) / len(R) / 1000 for p in pols}

    def cons(S, lam, z):
        u = lambda r, p: 100 * r[p][0] - lam * r[p][1] / 1000
        D = {p: [u(r, p) - u(r, default) for r in S] for p in pols if p != default}
        p = max(D, key=lambda q: sum(D[q]))
        mu = sum(D[p]) / len(S); sd = (sum((x - mu) ** 2 for x in D[p]) / (len(S) - 1)) ** 0.5
        return p if mu > z * sd / len(S) ** 0.5 else default

    for lam in (0.0, 0.5, 2.0):
        reg, fixed, best, by_model = {k: [] for k in ks}, {p: [] for p in pols}, Counter(), {}
        creg = {(k, z): [] for k in ks for z in zs}; sw = {(k, z): [] for k in ks for z in zs}; treg = {k: [] for k in ks}
        for name, R in rows.items():
            Uf = U(R, lam); b = max(Uf, key=Uf.get); best[b] += 1
            for p in pols:
                fixed[p].append(Uf[b] - Uf[p])
            for k in ks:
                r, c, tr = [], {z: [] for z in zs}, []
                for _ in range(reps):
                    S = rng.sample(R, min(k, len(R))); Up = U(S, lam); r.append(Uf[b] - Uf[max(Up, key=Up.get)])
                    if alt:
                        tr.append(Uf[b] - Uf[alt if sum(x[default][1] for x in S) > sum(x[alt][1] for x in S) else default])
                    for z in zs:
                        q = cons(S, lam, z); c[z].append(Uf[b] - Uf[q]); sw[(k, z)].append(q != default)
                reg[k].append(sum(r) / len(r))
                if alt:
                    treg[k].append(sum(tr) / len(tr))
                for z in zs:
                    creg[(k, z)].append(sum(c[z]) / len(c[z]))
                if k == 30:
                    bm = by_model.setdefault(name[0], {"pilot": [], "cons": [], "default": []})
                    bm["pilot"].append(sum(r) / len(r)); bm["cons"].append(sum(c[zs[0]]) / len(c[zs[0]])); bm["default"].append(Uf[b] - Uf[default])
        fx = {p: sum(v) / len(v) for p, v in fixed.items()}; bf = min(fx, key=fx.get); p30 = sum(reg[30]) / len(reg[30])
        mean = lambda v: sum(v) / len(v)
        print(f"  lambda {lam}: {len(rows)} cells | pilot regret " + ", ".join(f"k={k} {mean(v):.2f}" for k, v in reg.items())
              + " | conservative (z " + "/".join(f"{z:.2f}" for z in zs) + ") " + ", ".join(
                  f"k={k} {mean(creg[(k, zs[0])]):.2f}/{mean(creg[(k, zs[1])]):.2f} (switch {100 * mean(sw[(k, zs[0])]):.0f}%/{100 * mean(sw[(k, zs[1])]):.0f}%)" for k in ks)
              + (" | token switch to " + alt + " " + ", ".join(f"k={k} {mean(v):.2f}" for k, v in treg.items()) if alt else "")
              + f" | always: " + ", ".join(f"{p} {v:.2f}" for p, v in fx.items()) + f" | best per cell {dict(best)}"
              + " | k=30 by model (pilot / conservative / default) " + ", ".join(
                  f"{m} {mean(v['pilot']):.2f}/{mean(v['cons']):.2f}/{mean(v['default']):.2f}" for m, v in by_model.items()))
        if lam == 0.5:
            c30 = mean(creg[(30, zs[0])])
            print(f"  *** PX: k=30 pilot {p30:.2f} | default {default} {fx[default]:.2f} (PX-1 {p30 < fx[default]}) | PX-2 {p30 <= 1.5} | "
                  f"best fixed {bf} {fx[bf]:.2f} (PX-3 {p30 < fx[bf]})")
            print(f"  *** PX2: k=30 conservative {c30:.2f} | in-sample bound min(default, pilot) + 0.25 = {min(fx[default], p30) + 0.25:.2f} "
                  f"(PX2-2 {c30 <= min(fx[default], p30) + 0.25}) | by model, conservative <= pilot and <= default (PX2-1): " + ", ".join(
                      f"{m} {mean(v['cons']) <= mean(v['pilot']) and mean(v['cons']) <= mean(v['default'])}" for m, v in by_model.items()))
            if alt:
                t30 = mean(treg[30])
                print(f"  *** SQL-P6: always {default} {fx[default]:.2f} < k=30 pilot {p30:.2f}: {fx[default] < p30} | SQL-P7: token switch {t30:.2f} "
                      f"<= {fx[default]:.2f} + 0.1: {t30 <= fx[default] + 0.1}")


def cell(m, seeds=(1, 2, 3)):
    diff = {r["id"]: r["difficulty"] for r in map(json.loads, open(ITEMS))}
    per, tok, n, leak = {}, Counter(), Counter(), Counter()
    G = {s: json.load(open(f"{RES}/grades_{m}_s{s}.json")) for s in seeds if os.path.exists(f"{RES}/grades_{m}_s{s}.json")}
    if JOIN:
        G = {s: {i: {a: x.get("join", x) for a, x in g.items()} for i, g in Gs.items()} for s, Gs in G.items()}
    if len(G) < len(seeds):
        return None
    for s in seeds:
        s2 = seeds[(seeds.index(s) + 1) % len(seeds)]
        C, T, SB = ({r["id"]: r for r in _rows(f"{RES}/{m}_{a}_s{s}.jsonl")} for a in ("cheap", TARM, "sb"))
        T2 = {r["id"]: r for r in _rows(f"{RES}/{m}_{TARM}_s{s2}.jsonl")}
        for i, c in C.items():
            g, g2 = G[s].get(i, {}), G[s2].get(i, {})
            if TG != "T":
                g, g2 = ({**x, "T": x[TG]} if TG in x else {} for x in (g, g2))
            if i not in T or i not in SB or i not in T2 or not all(a in g for a in ("N", "T", "SB")) or "T" not in g2:
                continue
            ok = {a: g[a]["ok"] for a in ("N", "T", "SB")}; ck = {a: g[a]["chk"] for a in ("N", "T", "SB")}
            nt, st, tt, t2t = c["n_tok"], SB[i]["out_tokens"], T[i]["out_tokens"], T2[i]["out_tokens"]
            yes = "yes" in c.get("s_ans", "")
            res = {"N": (ok["N"], nt), "T": (ok["T"], tt), "SB": (ok["SB"], st),
                   "S": ((ok["T"], c["s_tok"] + tt) if yes else (ok["N"], c["s_tok"] + nt)),
                   "N->T": ((ok["N"], nt) if ck["N"] else (ok["T"], nt + tt)),
                   "N->SB->T": ((ok["N"], nt) if ck["N"] else (ok["SB"], nt + st) if ck["SB"] else (ok["T"], nt + st + tt)),
                   "SB->T->T": ((ok["SB"], st) if ck["SB"] else (ok["T"], st + tt) if ck["T"] else (g2["T"]["ok"], st + tt + t2t)),
                   "T->T": ((ok["T"], tt) if ck["T"] else (g2["T"]["ok"], tt + t2t)),
                   "N->T|hidden": ((True, nt) if ok["N"] else (ok["T"], nt + tt))}
            per.setdefault(i, []).append({k: bool(v[0]) for k, v in res.items()})
            ROWS.setdefault((m, s), []).append({k: (bool(v[0]), v[1]) for k, v in res.items()})
            for k, v in res.items():
                tok[k] += v[1]; tok[(k, diff[i])] += v[1]
            n["all"] += 1; n[diff[i]] += 1
            for a in ("N", "SB", "T"):
                leak[(a, "chk")] += ck[a]
                if ck[a] and not ok[a]:
                    leak[(a, "leak")] += 1; leak[(a, g[a]["err"])] += 1
    return per, tok, n, leak, diff


def main():
    global TARM, TG
    score = Counter(); cells = 0
    for a in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a", "q35g"]:
        m, _, arm = a.partition(":")
        TARM = arm or os.environ.get("LCB_THINK", "think"); TG = TGS[TARM]
        r = cell(m, tuple(int(x) for x in os.environ.get("LCB_SEEDS", "1,2,3").split(",")))
        if not r or not r[2]["all"]:
            print(f"=== {m}: no complete rows"); continue
        per, tok, n, leak, diff = r; cells += 1
        acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n["all"] for k in POL}
        kt = {k: tok[k] / n["all"] / 1000 for k in POL}
        u = {k: acc[k] - LAM * kt[k] for k in POL}
        print(f"=== {m} ({len(per)} problems, {n['all']} rows)")
        print("  " + " | ".join(f"{k} {acc[k]:.1f}% @ {kt[k]:.2f}k u {u[k]:.1f}" for k in POL))
        for a in ("N", "SB", "T"):
            lk = {k[1]: v for k, v in leak.items() if k[0] == a and k[1] not in ("chk", "leak")}
            print(f"  {a}: passes the samples {100 * leak[(a, 'chk')] / n['all']:.1f}%, leak {leak[(a, 'leak')]} of {leak[(a, 'chk')]} "
                  f"({100 * leak[(a, 'leak')] / max(1, leak[(a, 'chk')]):.1f}%; first hidden failure {dict(lk)})")
        d = lambda a, c: ci({i: sum(x[a] - x[c] for x in v) / len(v) for i, v in per.items()})
        for a, c in (("N->T", "T"), ("SB->T->T", "T->T"), ("N->SB->T", "T"), ("N->T|hidden", "N->T"), ("T", "N"), ("N->T", "S")):
            mu, lo, hi = d(a, c)
            print(f"  {a} - {c} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] at {100 * tok[a] / max(1, tok[c]):.0f}% of its tokens")
        for dd in ("easy", "medium", "hard"):
            ids = [i for i in per if diff[i] == dd]
            if ids:
                rows = [x for i in ids for x in per[i]]
                print(f"  {dd} ({len(ids)}): " + " | ".join(
                    f"{k} {100 * sum(x[k] for x in rows) / len(rows):.0f}% @ {tok[(k, dd)] / len(rows) / 1000:.1f}k "
                    f"({100 * tok[(k, dd)] / max(1, tok[k]):.0f}% of its tokens)" for k in ("N", "T", "N->T", "SB->T->T", "T->T")))
        tie = lambda a, c: d(a, c)[2] >= 0 and tok[a] <= 0.90 * tok[c]   # HO-CC's CC-P1: the paired upper bound >= 0 at <= 90% tokens
        score["P1"] += tie("SB->T->T", "T->T")
        score["P2"] += tie("N->T", "T")
        score["P3"] += leak[("N", "leak")] >= 0.10 * leak[("N", "chk")]
        score["P4"] += acc["N->T|hidden"] >= acc["N->T"] + 2.0
    print(f"*** {cells} models: LC-P1 {score['P1']}; LC-P2 {score['P2']}; LC-P3 {score['P3']}; LC-P4 {score['P4']} (each needs >= 2 of 3)")
    if PILOT:
        print("PX pilot, contest code:")
        pilot(ROWS, [p for p in POL if p != "N->T|hidden"], "SB->T->T")


if __name__ == "__main__":
    main()
