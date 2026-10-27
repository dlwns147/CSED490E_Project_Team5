"""TC-1 (docs/prereg/PREREG_TC.md): policies on tool calling from run_tc.py rows and grade_tc.py grades (BFCL's own checker). Per item
and seed (tokens = every call's output tokens; s' = the next seed, s mod 3 + 1):
  N, T, SB              one non-thinking / thinking / 2k-cut response
  S                     self-selective reasoning (Li et al. 2025 style): T if the model said yes, else N (+ the yes / no call)
  N->T                  N; T where the free check (schema validation) fails on N
  SB->T                 the recipe as stated: SB; T where the check fails on SB
  T->T                  the check-matched think: T; seed s' T where the check fails on T
  2N->T                 DART-style agreement (2606.23181, without its entropy budget): N and seed s' N; N if their calls agree, else T
  N->T|ag               N and seed s' N; T where the check fails on N or the two disagree
  SB->T|ag              N and SB; T where the check fails on SB or N's calls differ from SB's (else SB)
Utility = accuracy - 0.5 x ktokens. Paired 95% intervals over items (seed means). Cells: model x {non-live, live}. Also: the check's
power (share of wrong N it fails) and false alarms (share of right N it fails), agreement rates, oracle(N, T), per-category accuracy.
usage: python analyze_tc.py [model ...]   (default q8b q14a q35)"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl", "tc_items.jsonl")
POL = ("N", "T", "SB", "S", "N->T", "SB->T", "T->T", "2N->T", "N->T|ag", "SB->T|ag")
LAM = 0.5
NONLIVE = ("simple_python", "multiple", "parallel", "parallel_multiple", "irrelevance")


def load(m, s):
    gp = f"{RES}/grades_{m}_s{s}.json"
    if not os.path.exists(gp):
        return None
    return (json.load(open(gp)),) + tuple({r["id"]: r for r in _rows(f"{RES}/{m}_{a}_s{s}.jsonl")} for a in ("cheap", "think", "sb"))


def cell(m, split, cats):
    per, tok, n, ck, cat_acc = {}, dict.fromkeys(POL + ("oracle",), 0), 0, Counter(), {}
    D = {s: load(m, s) for s in (1, 2, 3)}
    if any(v is None for v in D.values()):
        return None
    for s in (1, 2, 3):
        G, C, T, SB = D[s]; G2, C2, T2, _ = D[s % 3 + 1]
        for i, c in C.items():
            if cats.get(i) is None or (cats[i] in NONLIVE) != (split == "non-live"):
                continue
            if i not in T or i not in SB or i not in G or i not in G2 or i not in C2 or i not in T2 or not {"N", "T", "SB"} <= set(G[i]) \
                    or not {"N", "T"} <= set(G2[i]):
                continue
            g, g2 = G[i], G2[i]; n += 1
            ok = {a: g[a]["ok"] for a in ("N", "T", "SB")}
            nt, n2t, tt, st, t2t = c["n_tok"], C2[i]["n_tok"], T[i]["out_tokens"], SB[i]["out_tokens"], T2[i]["out_tokens"]
            fn, fs, ft = (g[a]["chk"] == "fail" for a in ("N", "SB", "T"))
            agree_nn, agree_ns = g["N"]["calls"] == g2["N"]["calls"], g["N"]["calls"] == g["SB"]["calls"]
            yes = "yes" in c.get("s_ans", "")
            ck["wrong"] += not ok["N"]; ck["caught"] += fn and not ok["N"]; ck["right"] += ok["N"]; ck["fa"] += fn and ok["N"]
            ck["dis_nn"] += not agree_nn; ck["dis_ns"] += not agree_ns; ck["sbcut"] += SB[i].get("think_tokens", 0) >= 2000
            ck["yes"] += yes; ck["dis_nn_wrong"] += (not agree_nn) and not ok["N"]
            res = {"N": (ok["N"], nt), "T": (ok["T"], tt), "SB": (ok["SB"], st),
                   "S": ((ok["T"], c["s_tok"] + tt) if yes else (ok["N"], c["s_tok"] + nt)),
                   "N->T": ((ok["T"], nt + tt) if fn else (ok["N"], nt)),
                   "SB->T": ((ok["T"], st + tt) if fs else (ok["SB"], st)),
                   "T->T": ((g2["T"]["ok"], tt + t2t) if ft else (ok["T"], tt)),
                   "2N->T": ((ok["N"], nt + n2t) if agree_nn else (ok["T"], nt + n2t + tt)),
                   "N->T|ag": ((ok["T"], nt + n2t + tt) if fn or not agree_nn else (ok["N"], nt + n2t)),
                   "SB->T|ag": ((ok["T"], nt + st + tt) if fs or not agree_ns else (ok["SB"], nt + st)),
                   "oracle": (ok["N"] or ok["T"], nt + tt)}
            per.setdefault(i, []).append({k: bool(v[0]) for k, v in res.items()})
            for k, v in res.items():
                tok[k] += v[1]
            for a in ("N", "T", "SB"):
                cat_acc.setdefault(cats[i], Counter())[a] += ok[a]
            cat_acc[cats[i]]["n"] += 1
    return per, tok, n, ck, cat_acc


def main():
    cats = {x["id"]: x["cat"] for x in (json.loads(l) for l in open(DATA))}
    score = Counter(); cells = 0
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a", "q35"]:
        for split in ("non-live", "live"):
            r = cell(m, split, cats)
            if not r or not r[2]:
                print(f"=== {m} {split}: no complete rows"); continue
            per, tok, n, ck, cat_acc = r; cells += 1
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in POL + ("oracle",)}
            kt = {k: tok[k] / n / 1000 for k in POL + ("oracle",)}
            u = {k: acc[k] - LAM * kt[k] for k in POL}
            power = 100 * ck["caught"] / max(1, ck["wrong"])
            print(f"=== {m} {split} ({len(per)} items, {n} rows; the check fails {power:.0f}% of wrong N (power), "
                  f"{100 * ck['fa'] / max(1, ck['right']):.0f}% of right N (false alarm); N/N' disagree {100 * ck['dis_nn'] / n:.0f}% "
                  f"(of wrong N: {100 * ck['dis_nn_wrong'] / max(1, ck['wrong']):.0f}%), N/SB {100 * ck['dis_ns'] / n:.0f}%; SB cut "
                  f"{100 * ck['sbcut'] / n:.0f}%; says yes {100 * ck['yes'] / n:.0f}%; oracle(N, T) {acc['oracle']:.1f}%)")
            print("  " + " | ".join(f"{k} {acc[k]:.1f}% @ {kt[k]:.2f}k u {u[k]:.1f}" for k in POL))
            print("  per category N / T / SB: " + "; ".join(f"{c} {100 * v['N'] / v['n']:.0f}/{100 * v['T'] / v['n']:.0f}/"
                                                       f"{100 * v['SB'] / v['n']:.0f} (n={v['n']})" for c, v in sorted(cat_acc.items())))
            d = lambda a, c: ci({i: sum(x[a] - x[c] for x in v) / len(v) for i, v in per.items()})
            for a, c in (("N->T|ag", "N->T"), ("N->T|ag", "T"), ("N->T|ag", "2N->T"), ("SB->T", "T"), ("T", "N"), ("N->T|ag", "S")):
                mu, lo, hi = d(a, c)
                print(f"  {a} - {c} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] at {100 * tok[a] / max(1, tok[c]):.0f}% of its tokens")
            score["P1"] += power < 25
            score["P2"] += acc["N->T|ag"] >= acc["N->T"] + 1.0
            score["P3"] += acc["N->T|ag"] >= acc["T"] - 1.0 and tok["N->T|ag"] <= 0.5 * tok["T"]
            score["P4"] += u["N->T|ag"] >= u["2N->T"]
            score["P5"] += acc["SB->T"] >= acc["T"] - 1.0 and u["SB->T"] >= u["T"]
    print(f"*** {cells} cells: TC-P1 {score['P1']}; TC-P2 {score['P2']}; TC-P3 {score['P3']}; TC-P4 {score['P4']}; TC-P5 {score['P5']}")


if __name__ == "__main__":
    main()
