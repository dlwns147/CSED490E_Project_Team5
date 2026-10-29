"""SQL-1 (docs/prereg/PREREG_SQL.md): policies on text-to-SQL from run_sql.py rows and grade_sql.py grades (BIRD's execution accuracy).
Per question and seed (tokens = every call's output tokens; s' = the next seed, s mod 3 + 1; the free check = the query runs and returns
rows — for N as the client saw it when it chose to repair, for T / SB from the grade):
  N, T, SB         one non-thinking / thinking / 2k-cut query
  S                self-selective reasoning (Li et al. 2025 style): T if the model said yes, else N (+ the yes / no call)
  N->R             N; one non-thinking rewrite from what the check saw, where N fails it
  N->T             cheap first: N; T where N fails the check
  N->R->T          N; R where N fails; T where R fails too
  SB->T            SB; T where SB fails
  SB->T->T         the default order: SB; T where SB fails; seed s' T where T fails too
  T->T             the check-matched think: T; seed s' T where T fails
  2N->T            N and seed s' N; N if their result rows agree, else T (DART-style)
  N->T|ag          N and seed s' N; T where N fails the check or they disagree
Utility = accuracy - 0.5 x ktokens. Paired 95% intervals over questions (seed means). Also the leak (N passes the check, wrong) with
what the wrong ones return, the check's false alarms, accuracy by difficulty, thinks at the cap, S's yes-rate.
--pilot (SQL-P6 / P7): PX's pilot, PX2's gated pilot and the token switch to T->T on the 9 model x seed cells.
usage: python analyze_sql.py [--pilot] [tag ...]   (default q8b q14a q35)"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from prep_sql import DATA  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
POL = ("N", "T", "SB", "S", "N->R", "N->T", "N->R->T", "SB->T", "SB->T->T", "T->T", "2N->T", "N->T|ag")
LAM = 0.5
ROWS = {}   # --pilot: (tag, seed) -> one {policy: (right, tokens)} per question


def cell(m):
    diff = {r["id"]: r["difficulty"] for r in map(json.loads, open(f"{DATA}/sql_items.jsonl"))}
    G, C, T, SB = {}, {}, {}, {}
    for s in (1, 2, 3):
        gp = f"{RES}/grades_{m}_s{s}.json"
        if not os.path.exists(gp):
            return None
        G[s] = json.load(open(gp)); G[s].pop("_gold_fail", None)
        C[s], T[s], SB[s] = ({r["id"]: r for r in _rows(f"{RES}/{m}_{a}_s{s}.jsonl")} for a in ("cheap", "think", "sb"))
    per, tok, n, ck = {}, Counter(), Counter(), Counter()
    for s in (1, 2, 3):
        s2 = s % 3 + 1
        for i, c in C[s].items():
            g, g2 = G[s].get(i, {}), G[s2].get(i, {})
            if not {"N", "T", "SB"} <= set(g) or not {"N", "T"} <= set(g2) or i not in T[s] or i not in SB[s] or i not in T[s2] \
                    or i not in C[s2] or (c["c_n"] != "pass" and "R" not in g):
                continue
            fn, fs, ft = c["c_n"] != "pass", g["SB"]["chk"] != "pass", g["T"]["chk"] != "pass"
            fr = fn and g["R"]["chk"] != "pass"
            nt, n2t, tt, st, t2t = c["n_tok"], C[s2][i]["n_tok"], T[s][i]["out_tokens"], SB[s][i]["out_tokens"], T[s2][i]["out_tokens"]
            rt = c.get("r_tok", 0)
            ag = g["N"]["h"] is not None and g["N"]["h"] == g2["N"]["h"]
            ok = {a: g[a]["ok"] for a in g}; t2ok = g2["T"]["ok"]
            yes = "yes" in c.get("s_ans", "")
            res = {"N": (ok["N"], nt), "T": (ok["T"], tt), "SB": (ok["SB"], st),
                   "S": ((ok["T"], c["s_tok"] + tt) if yes else (ok["N"], c["s_tok"] + nt)),
                   "N->R": ((ok["R"], nt + rt) if fn else (ok["N"], nt)),
                   "N->T": ((ok["T"], nt + tt) if fn else (ok["N"], nt)),
                   "N->R->T": (((ok["T"], nt + rt + tt) if fr else (ok["R"], nt + rt)) if fn else (ok["N"], nt)),
                   "SB->T": ((ok["T"], st + tt) if fs else (ok["SB"], st)),
                   "SB->T->T": ((ok["SB"], st) if not fs else (ok["T"], st + tt) if not ft else (t2ok, st + tt + t2t)),
                   "T->T": ((ok["T"], tt) if not ft else (t2ok, tt + t2t)),
                   "2N->T": ((ok["N"], nt + n2t) if ag else (ok["T"], nt + n2t + tt)),
                   "N->T|ag": ((ok["T"], nt + n2t + tt) if fn or not ag else (ok["N"], nt + n2t))}
            per.setdefault(i, []).append({k: bool(v[0]) for k, v in res.items()})
            ROWS.setdefault((m, s), []).append({k: (bool(v[0]), v[1]) for k, v in res.items()})
            for k, v in res.items():
                tok[k] += v[1]; tok[(k, diff[i])] += v[1]
            n["all"] += 1; n[diff[i]] += 1
            ck["n_pass"] += not fn; ck["n_leak"] += (not fn) and not ok["N"]; ck["n_right"] += ok["N"]
            ck["n_fa"] += fn and ok["N"]; ck["n_wrong"] += not ok["N"]; ck["n_caught"] += fn and not ok["N"]
            ck["mismatch"] += (c["c_n"] == "pass") != (g["N"]["chk"] == "pass")
            ck["fail_" + ("error" if fn and c["c_n"] not in ("no rows", "timeout") else c["c_n"] if fn else "pass")] += 1
            ck["t_cap"] += T[s][i].get("finish") == "length"; ck["sb_cut"] += SB[s][i].get("think_tokens", 0) >= 2000
            ck["yes"] += yes
            for a in ("SB", "T"):
                ck[a + "_pass"] += g[a]["chk"] == "pass"; ck[a + "_leak"] += g[a]["chk"] == "pass" and not ok[a]
    return per, tok, n, ck, diff


def main():
    score = Counter(); cells = 0
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a", "q35"]:
        r = cell(m)
        if not r or not r[2]["all"]:
            print(f"=== {m}: no complete rows"); continue
        per, tok, n, ck, diff = r; cells += 1
        acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n["all"] for k in POL}
        kt = {k: tok[k] / n["all"] / 1000 for k in POL}
        u = {k: acc[k] - LAM * kt[k] for k in POL}
        N = n["all"]
        print(f"=== {m} ({len(per)} questions, {N} rows; N passes the check {100 * ck['n_pass'] / N:.0f}% (fails: error "
              f"{100 * ck['fail_error'] / N:.1f}%, no rows {100 * ck['fail_no rows'] / N:.1f}%, timeout {100 * ck['fail_timeout'] / N:.1f}%), "
              f"leak {ck['n_leak']} of {ck['n_pass']} ({100 * ck['n_leak'] / max(1, ck['n_pass']):.1f}%); the check fails "
              f"{100 * ck['n_caught'] / max(1, ck['n_wrong']):.0f}% of wrong N (power), {100 * ck['n_fa'] / max(1, ck['n_right']):.1f}% of "
              f"right N (false alarm); SB leak {100 * ck['SB_leak'] / max(1, ck['SB_pass']):.1f}%, T leak "
              f"{100 * ck['T_leak'] / max(1, ck['T_pass']):.1f}%; T at its cap {100 * ck['t_cap'] / N:.1f}%, SB cut {100 * ck['sb_cut'] / N:.0f}%; "
              f"says yes {100 * ck['yes'] / N:.0f}%; online / offline check differ on {ck['mismatch']} N rows)")
        print("  " + " | ".join(f"{k} {acc[k]:.1f}% @ {kt[k]:.2f}k u {u[k]:.1f}" for k in POL))
        d = lambda a, c: ci({i: sum(x[a] - x[c] for x in v) / len(v) for i, v in per.items()})
        for a, c in (("N->T", "T"), ("SB->T->T", "T->T"), ("N->R", "N->T"), ("N->T|ag", "N->T"), ("N->R->T", "T"), ("T", "N"), ("N->T", "S")):
            mu, lo, hi = d(a, c)
            print(f"  {a} - {c} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] at {100 * tok[a] / max(1, tok[c]):.0f}% of its tokens")
        for dd in ("simple", "moderate", "challenging"):
            ids = [i for i in per if diff[i] == dd]
            rows = [x for i in ids for x in per[i]]
            if rows:
                print(f"  {dd} ({len(ids)}): " + " | ".join(f"{k} {100 * sum(x[k] for x in rows) / len(rows):.0f}% @ "
                                                         f"{tok[(k, dd)] / len(rows) / 1000:.2f}k" for k in ("N", "T", "N->T", "N->R", "SB->T->T", "T->T")))
        tie = lambda a, c, f: d(a, c)[2] >= 0 and tok[a] <= f * tok[c]
        score["P1"] += ck["n_leak"] >= 0.25 * ck["n_pass"]
        score["P2"] += tie("N->T", "T", 0.90)
        score["P3"] += tie("SB->T->T", "T->T", 0.90)
        score["P4"] += tie("N->R", "N->T", 0.50)
        score["P5"] += acc["N->T|ag"] >= acc["N->T"] + 1.0
    print(f"*** {cells} models: SQL-P1 {score['P1']}; SQL-P2 {score['P2']}; SQL-P3 {score['P3']}; SQL-P4 {score['P4']}; "
          f"SQL-P5 {score['P5']} (each needs >= 2 of 3)")
    if "--pilot" in sys.argv:
        from analyze_lcb import pilot
        print("SQL-P6 / P7 pilot, text-to-SQL:")
        pilot(ROWS, list(POL), "SB->T->T", alt="T->T")


if __name__ == "__main__":
    main()
