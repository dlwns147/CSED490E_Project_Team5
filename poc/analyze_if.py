"""IF-1 (docs/prereg/PREREG_IF.md): policies on instruction following from run_if.py rows and grade_if.py grades (official strict
grader, prompt level = every instruction followed). Per prompt and seed (tokens = every call's output tokens, the checker included):
  N, T, SB              one non-thinking / thinking / 2k-cut response
  S                     self-selective reasoning (Li et al. 2025 style): T if the model said yes, else N (+ the yes/no call)
  N->T                  check-gated thinking: N; T where the model's own checker fails on N (a checker that does not run: no signal)
  N->R                  DVR-style: N; one non-thinking rewrite given the checker's violations where it fails
  N->R->T               N; rewrite on a failed check; T if the rewrite fails it too
  SB->T                 the recipe's order: SB; T where the checker fails on SB
  T->T                  the check-matched think: T; the next seed's T where the checker fails on T
Utility = accuracy - 0.5 x ktokens. Paired 95% intervals over prompts (seed means). Also the checker: share that runs, its false
passes (passes N, the grader fails it) and false alarms (fails N, the grader passes it), and oracle(N, T) as a diagnostic.
usage: python analyze_if.py [model ...]   (default q8b q14a q35)"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "if")
POL = ("N", "T", "SB", "S", "N->T", "N->R", "N->R->T", "SB->T", "T->T")
LAM = 0.5


def cell(m, b):
    per, tok, n, ck = {}, dict.fromkeys(POL + ("oracle",), 0), 0, {"run": 0, "fp": 0, "wrong": 0, "fa": 0, "right": 0}
    for s in (1, 2, 3):
        gp = f"{RES}/grades_{b}_{m}_s{s}.json"
        if not os.path.exists(gp):
            return None
        G = json.load(open(gp))
        C, T, SB, K = ({r["id"]: r for r in _rows(f"{RES}/{b}_{m}_{a}_s{s}.jsonl")} for a in ("cheap", "think", "sb", "check"))
        T2 = {r["id"]: r for r in _rows(f"{RES}/{b}_{m}_think_s{s % 3 + 1}.jsonl")}
        G2 = json.load(open(f"{RES}/grades_{b}_{m}_s{s % 3 + 1}.json")) if os.path.exists(f"{RES}/grades_{b}_{m}_s{s % 3 + 1}.json") else {}
        for i, c in C.items():
            if i not in T or i not in SB or i not in K or i not in G or i not in T2 or "T" not in G2.get(i, {}):
                continue
            g = {a: all(v["strict"]) for a, v in G[i].items()}; t2 = all(G2[i]["T"]["strict"]); n += 1
            nt, ct, tt, st, t2t = c["n_tok"], c["c_tok"], T[i]["out_tokens"], SB[i]["out_tokens"], T2[i]["out_tokens"]
            fn, fs, ft = c["c_n"] == "fail", K[i]["c_sb"] == "fail", K[i]["c_t"] == "fail"
            fr = c.get("c_r") == "fail"
            yes = "yes" in c.get("s_ans", "")
            ck["run"] += c["c_n"] != "error"
            if c["c_n"] == "pass":
                ck["fp"] += not g["N"]
            ck["wrong"] += not g["N"]; ck["right"] += g["N"]; ck["fa"] += fn and g["N"]
            res = {"N": (g["N"], nt), "T": (g["T"], tt), "SB": (g["SB"], st),
                   "S": ((g["T"], c["s_tok"] + tt) if yes else (g["N"], c["s_tok"] + nt)),
                   "N->T": ((g["T"], ct + nt + tt) if fn else (g["N"], ct + nt)),
                   "N->R": ((g["R"], ct + nt + c["r_tok"]) if fn else (g["N"], ct + nt)),
                   "N->R->T": (((g["T"], ct + nt + c["r_tok"] + tt) if fr else (g["R"], ct + nt + c["r_tok"])) if fn else (g["N"], ct + nt)),
                   "SB->T": ((g["T"], ct + st + tt) if fs else (g["SB"], ct + st)),
                   "T->T": ((t2, ct + tt + t2t) if ft else (g["T"], ct + tt)),
                   "oracle": (g["N"] or g["T"], nt + tt)}
            per.setdefault(i, []).append({k: bool(v[0]) for k, v in res.items()})
            for k, v in res.items():
                tok[k] += v[1]
    return per, tok, n, ck


def main():
    score = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "P5": 0}; cells = 0
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a", "q35"]:
        for b in ("ifeval", "ifbench"):
            r = cell(m, b)
            if not r or not r[2]:
                print(f"=== {m} {b}: no complete rows"); continue
            per, tok, n, ck = r; cells += 1
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in POL + ("oracle",)}
            kt = {k: tok[k] / n / 1000 for k in POL + ("oracle",)}
            u = {k: acc[k] - LAM * kt[k] for k in POL}
            print(f"=== {m} {b} ({len(per)} prompts, {n} rows; checker runs on {100 * ck['run'] / n:.0f}%, passes {100 * ck['fp'] / max(1, ck['wrong']):.0f}% "
                  f"of wrong N (false pass), fails {100 * ck['fa'] / max(1, ck['right']):.0f}% of right N (false alarm); oracle(N, T) {acc['oracle']:.1f}%)")
            print("  " + " | ".join(f"{k} {acc[k]:.1f}% @ {kt[k]:.2f}k u {u[k]:.1f}" for k in POL))
            d = lambda a, c: ci({i: sum(x[a] - x[c] for x in v) / len(v) for i, v in per.items()})
            for a, c in (("N->T", "T"), ("N->T", "N"), ("N->R", "N->T"), ("N->T", "S"), ("N->T", "T->T"), ("T", "N")):
                mu, lo, hi = d(a, c)
                print(f"  {a} - {c} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] at {100 * tok[a] / max(1, tok[c]):.0f}% of its tokens")
            score["P1"] += acc["N->T"] >= acc["T"] - 1.0 and tok["N->T"] <= 0.5 * tok["T"]
            score["P2"] += acc["N->T"] >= max(acc["N"], acc["T"]) + 1.0
            score["P3"] += acc["N->R"] >= acc["N->T"]
            score["P4"] += acc["N->T"] >= acc["S"] + 1.0
            score["P5"] += u["N->T"] >= u["T->T"]
    print(f"*** {cells} cells: IF-P1 {score['P1']}; IF-P2 {score['P2']}; IF-P3 {score['P3']}; IF-P4 {score['P4']}; IF-P5 {score['P5']}")


if __name__ == "__main__":
    main()
