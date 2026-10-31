"""MT exploratory (FINDINGS 2026-10-31 15:1x UTC): can a peer see the silent failures of an agent turn? At turn 0 every N trajectory of an
item starts from the same conversation and the same environment state, so the three seeds of one model are three independent
non-thinking rollouts of that turn, and another model's rollouts are rollouts of the same turn too. For each rollout and one peer
rollout (the next seed of the same model, or the same seed of the peer model), agreement on the turn's calls, on the end state of
every involved instance (BFCL's _compare_instances), and on the end state plus the set of non-error results; against the rollout's
turn-0 correctness (BFCL's per-turn check: the state after the turn equals the ground truth's; for a non-empty ground truth, a
non-empty answer whose results contain the ground truth's) and whether the turn showed a visible failure (an error or a repeat).
Strata RV / RS / WV / WS as in PREREG_MT. Runs on the login node in the grader venv (seconds):
  /home1/leesangjun/venvs/bfcl/bin/python poc/mt_peer0.py <tag> [peer tag]      (RESTRICT=<tag>: only items that tag has at every seed)"""
import copy, json, os, re, sys
from collections import Counter

import bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils as U
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import _compare_instances, response_checker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "tc")
DATA = os.environ.get("MT_ITEMS") or os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl", "mt_items.jsonl")


def rows(tag):
    return {s: {r["id"]: r for r in map(json.loads, open(f"{RES}/mt_{tag}_N_s{s}.jsonl"))} for s in (1, 2, 3)}


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
    tag = sys.argv[1]; ptag = sys.argv[2] if len(sys.argv) > 2 else tag
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
            out[key] = (ok, vis, steps, mi, good)
        for s in (1, 2, 3):
            ok, vis, calls, mi, good = out[("m", s)]
            _, _, pc, pi, pg = out[("m", s % 3 + 1)] if E is D else out[("p", s)]
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


if __name__ == "__main__":
    main()
