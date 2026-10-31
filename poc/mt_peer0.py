"""MT exploratory (FINDINGS 2026-10-31 15:1x UTC): can a peer see the silent failures of an agent turn? At turn 0 every N trajectory of an
item starts from the same conversation and the same environment state, so the three seeds of one model are three independent
non-thinking rollouts of that turn, and another model's rollouts are rollouts of the same turn too. For each rollout and one peer
rollout (the next seed of the same model, or the same seed of the peer model), agreement on the turn's calls, on the end state of
every involved instance (BFCL's _compare_instances), and on the end state plus the set of non-error results; against the rollout's
turn-0 correctness (BFCL's per-turn check: the state after the turn equals the ground truth's; for a non-empty ground truth, a
non-empty answer whose results contain the ground truth's) and whether the turn showed a visible failure (an error or a repeat).
Strata RV / RS / WV / WS as in PREREG_MT. --rescue: also the turn 0 of the arms E, F (thinks at the turn's first step) and T
(always) at the same seed, the counterfactual of thinking on a flagged turn: rescue (flagged, N wrong, the arm right) and damage
(flagged, N right, the arm wrong), and turn-0 accuracy / output tokens of N, the arm, and "N; on an end-state disagreement redo the turn
with the arm" (the peer's turn-0 tokens counted), and "N; on a visible failure redo the turn from its start with the arm" (MT-R's
rollback at turn 0, where the redo is the arm's own turn 0: same start state, context and step seeds), over the item-seeds where the
arm's row exists. Runs on the login node in the grader
venv (seconds):
  /home1/leesangjun/venvs/bfcl/bin/python poc/mt_peer0.py <tag> [peer tag] [--rescue]      (RESTRICT=<tag>: only items that tag has at every seed)"""
import copy, json, os, re, sys
from collections import Counter

import bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils as U
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import _compare_instances, response_checker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "tc")
DATA = os.environ.get("MT_ITEMS") or os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl", "mt_items.jsonl")


def _load(path):
    """rows of a file that running jobs may still be appending to (a torn last line is skipped)"""
    out = {}
    for line in open(path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        out[r["id"]] = r
    return out


def rows(tag, arm="N"):
    return {s: _load(f"{RES}/mt_{tag}_{arm}_s{s}.jsonl") for s in (1, 2, 3)}


def run(p, steps, name):
    """execute the turn's steps on fresh instances; the end instances and every result"""
    cfg, cls = p["initial_config"], p["involved_classes"]
    _, inst = U.execute_multi_turn_func_call([], cfg, cls, name, p["id"], long_context=False, is_evaL_run=True)
    out = []
    for c in steps:
        r, inst = U.execute_multi_turn_func_call(c, cfg, cls, name, p["id"], long_context=False, is_evaL_run=True)
        out += r
    inst = {k: copy.deepcopy(v) for k, v in inst.items()}
    for c in cls:
        U.__dict__.pop(re.sub(r"[-./:]", "_", f"{name}_{p['id']}_{c}_instance"), None)
    return inst, out


def same(a, b):
    return all(_compare_instances(a[k], b[k])[0] for k in a)


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    tag = pos[0]; ptag = pos[1] if len(pos) > 1 else tag
    XA = {a: rows(tag, a) for a in ("E", "F", "T")} if "--rescue" in sys.argv else {}
    RC = Counter()
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    D = rows(tag); E = rows(ptag) if ptag != tag else D
    ids = sorted(set.intersection(*(set(d) for d in list(D.values()) + list(E.values()))))
    if os.environ.get("RESTRICT"):
        F = rows(os.environ["RESTRICT"]); ids = [i for i in ids if all(i in F[s] for s in (1, 2, 3))]
    C = Counter()
    for i in ids:
        p = P[i]; gt = p["ground_truth"][0]
        gi, gres = run(p, [gt] if gt else [], "pgt")
        out = {}
        for key, X, s in [(("m", s), D, s) for s in (1, 2, 3)] + ([(("p", s), E, s) for s in (1, 2, 3)] if E is not D else []):
            x = X[s][i]; t0 = x["turns"][0] if x["turns"] else []
            steps = [st["calls"] for st in t0 if st["calls"]]
            mi, mres = run(p, steps, f"p{key[0]}{s}")
            ok = same(mi, gi) and not (x["force_quit"] and len(x["turns"]) == 1)
            if ok and gt:
                ok = bool(steps) and response_checker(mres, gres, 0)["valid"]
            vis = any(any(st.get("err") or []) or st.get("loop") for st in t0)
            good = sorted({r for r in mres if not r.startswith("Error during execution") and '"error"' not in r[:20]})
            out[key] = (ok, vis, steps, mi, good, sum(st["tok"] for st in t0))
        for s in (1, 2, 3):
            ok, vis, calls, mi, good, tk = out[("m", s)]
            _, _, pc, pi, pg, ptk = out[("m", s % 3 + 1)] if E is D else out[("p", s)]
            for a, R in XA.items():   # --rescue: the arm's own turn 0 from the same start
                if i not in R[s]:
                    continue
                x = R[s][i]; t0 = x["turns"][0] if x["turns"] else []
                st = [z["calls"] for z in t0 if z["calls"]]
                ai, ares = run(p, st, f"r{a}{s}")
                aok = same(ai, gi) and not (x["force_quit"] and len(x["turns"]) == 1)
                if aok and gt:
                    aok = bool(st) and response_checker(ares, gres, 0)["valid"]
                fl = not same(mi, pi)
                atk = sum(z["tok"] for z in t0)
                RC[(a, "n")] += 1; RC[(a, "okN")] += ok; RC[(a, "okA")] += aok; RC[(a, "tokN")] += tk; RC[(a, "tokA")] += atk
                RC[(a, "okP")] += aok if fl else ok; RC[(a, "tokP")] += tk + ptk + (atk if fl else 0)
                RC[(a, "okV")] += aok if vis else ok; RC[(a, "tokV")] += tk + (atk if vis else 0)   # MT-R: redo the turn from its start
                RC[(a, "flag", ok)] += fl; RC[(a, "fix" if not ok else "harm", fl)] += (aok != ok)
            k = ("R" if ok else "W") + ("V" if vis else "S")
            C[(k, "n")] += 1
            a = {"calls": calls == pc, "state": same(mi, pi)}
            a["state + results"] = a["state"] and good == pg
            for d, v in a.items():
                C[(k, d)] += v
    print(f"=== {tag} N, peer {ptag if ptag != tag else 'another seed'}: turn 0, {len(ids)} items x 3 seeds")
    for k in ("RV", "RS", "WV", "WS"):
        n = max(1, C[(k, "n")])
        print(f"  {k} {C[(k, 'n')]}: peer agrees on " + "; ".join(f"{d} {100 * C[(k, d)] / n:.1f}%" for d in ("calls", "state", "state + results")))
    for d in ("calls", "state", "state + results"):
        print(f"  {d}: flags {100 - 100 * C[('RS', d)] / max(1, C[('RS', 'n')]):.1f}% of silent right turns, "
              f"{100 - 100 * C[('WS', d)] / max(1, C[('WS', 'n')]):.1f}% of silent wrong turns")
    for a in XA:
        n = max(1, RC[(a, "n")])
        print(f"  --rescue {a} ({RC[(a, 'n')]} item-seeds): turn-0 right N {100 * RC[(a, 'okN')] / n:.1f}% @ {RC[(a, 'tokN')] / n:.0f} tokens, "
              f"{a} {100 * RC[(a, 'okA')] / n:.1f}% @ {RC[(a, 'tokA')] / n:.0f}, N -> peer state differs -> {a}: {100 * RC[(a, 'okP')] / n:.1f}% @ "
              f"{RC[(a, 'tokP')] / n:.0f}; flagged: {RC[(a, 'flag', False)]} wrong N turns ({a} fixes {RC[(a, 'fix', True)]}), "
              f"{RC[(a, 'flag', True)]} right N turns ({a} breaks {RC[(a, 'harm', True)]}); unflagged wrong N turns {a} would fix: "
              f"{RC[(a, 'fix', False)]}; N -> visible failure -> redo the turn from its start with {a}: {100 * RC[(a, 'okV')] / n:.1f}% @ "
              f"{RC[(a, 'tokV')] / n:.0f}")


if __name__ == "__main__":
    main()
