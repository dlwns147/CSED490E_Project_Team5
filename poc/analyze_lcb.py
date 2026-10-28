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
LCB_THINK=thinkh (LC-OSS): gpt-oss's high-effort think (rows thinkh, grade TH) takes T's place in every policy (thinkh64: the same at a 64k cap).
usage: python analyze_lcb.py [tag ...]   (default q8b q14a q35g — Qwen3.5-9B at the general preset, the amendment; LCB_SEEDS=1 for the smoke, where T->T reuses the same seed)"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "lcb")
ITEMS = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "lcb", "lcb_items.jsonl")
POL = ("N", "T", "SB", "S", "N->T", "N->SB->T", "SB->T->T", "T->T", "N->T|hidden")
LAM = 0.5
TARM = os.environ.get("LCB_THINK", "think"); TG = {"think": "T", "thinkh": "TH", "thinkh64": "TH64"}[TARM]


def cell(m, seeds=(1, 2, 3)):
    diff = {r["id"]: r["difficulty"] for r in map(json.loads, open(ITEMS))}
    per, tok, n, leak = {}, Counter(), Counter(), Counter()
    G = {s: json.load(open(f"{RES}/grades_{m}_s{s}.json")) for s in seeds if os.path.exists(f"{RES}/grades_{m}_s{s}.json")}
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
            for k, v in res.items():
                tok[k] += v[1]; tok[(k, diff[i])] += v[1]
            n["all"] += 1; n[diff[i]] += 1
            for a in ("N", "SB", "T"):
                leak[(a, "chk")] += ck[a]
                if ck[a] and not ok[a]:
                    leak[(a, "leak")] += 1; leak[(a, g[a]["err"])] += 1
    return per, tok, n, leak, diff


def main():
    score = Counter(); cells = 0
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a", "q35g"]:
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


if __name__ == "__main__":
    main()
