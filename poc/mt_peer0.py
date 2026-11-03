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
  /home1/leesangjun/venvs/bfcl/bin/python poc/mt_peer0.py <tag> [peer tag] [--rescue] [--dump]      (RESTRICT=<tag>: only items that tag has at every seed;
  --dump, MT-B: results/tc/mt_turn0_<tag>.json, per item-seed the turn-0 calls N, peer N, T, next-seed T as (end-state group, no visible
  failure, right, tokens))"""
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
    DUMP = {} if "--dump" in sys.argv else None   # MT-B: per item-seed the turn-0 calls N, peer N, T, next-seed T
    TT = rows(tag, "T") if DUMP is not None else None
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
        if DUMP is not None and all(i in TT[s] for s in (1, 2, 3)):
            tout = {}
            for s in (1, 2, 3):
                x = TT[s][i]; t0 = x["turns"][0] if x["turns"] else []
                st = [z["calls"] for z in t0 if z["calls"]]
                ai, ares = run(p, st, f"t{s}")
                aok = same(ai, gi) and not (x["force_quit"] and len(x["turns"]) == 1)
                if aok and gt:
                    aok = bool(st) and response_checker(ares, gres, 0)["valid"]
                tout[s] = (aok, any(any(z.get("err") or []) or z.get("loop") for z in t0), ai, sum(z["tok"] for z in t0))
            for s in (1, 2, 3):
                cs = [out[("m", s)], out[("m", s % 3 + 1)] if E is D else out[("p", s)]]
                cs = [(c[0], c[1], c[3], c[5]) for c in cs] + [tout[s], tout[s % 3 + 1]]
                reps, obs = [], []
                for ok_, vis_, inst, tk_ in cs:   # end states as answers: the first earlier call with the same end state
                    g = next((k for k, r in enumerate(reps) if same(inst, r)), None)
                    if g is None:
                        reps.append(inst); g = len(reps) - 1
                    obs.append((f"s{g}", not vis_, bool(ok_), tk_))
                DUMP[f"{i}/{s}"] = obs
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
                RC[(a, "vfix" if not ok else "vharm", vis)] += (aok != ok)
                RC[(a, "flag", ok)] += fl; RC[(a, "fix" if not ok else "harm", fl)] += (aok != ok)
            k = ("R" if ok else "W") + ("V" if vis else "S")
            C[(k, "n")] += 1
            a = {"calls": calls == pc, "state": same(mi, pi)}
            a["state + results"] = a["state"] and good == pg
            for d, v in a.items():
                C[(k, d)] += v
    if DUMP is not None:
        json.dump(DUMP, open(os.path.join(RES, f"mt_turn0_{tag}.json"), "w"))
        print(f"dumped {len(DUMP)} item-seeds")
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
              f"{RC[(a, 'tokV')] / n:.0f} ({a} fixes {RC[(a, 'vfix', True)]} / breaks {RC[(a, 'vharm', True)]} visible-failure turns; "
              f"fixes {RC[(a, 'vfix', False)]} / breaks {RC[(a, 'vharm', False)]} of the rest)")


SEL_MODELS = ("q8b", "q14a", "q35")
SEL_PEER = {"q8b": "q35", "q14a": "q35", "q35": "q8b"}   # the cascade's peers (lcm_shift.PEER)
SEL_ARMS = ("N", "E", "F", "T")


def render(t0, cap=300, keep=(10, 2)):
    """MT-SEL: a turn's rollout as the verifier reads it — each step's calls and their results (each cut at `cap` characters), the
    closing reply; a turn of more than 12 steps keeps its first 10 and last 2, and the text its first 2,000 and last 1,000 characters"""
    st = [z for z in t0]
    if len(st) > sum(keep):
        st = st[:keep[0]] + [{"skip": len(st) - sum(keep)}] + st[-keep[1]:]
    out = []
    for z in st:
        if "skip" in z:
            out.append(f"... ({z['skip']} more steps) ..."); continue
        if z["calls"]:
            out.append(f"[{', '.join(z['calls'])}]")
            out += [f"-> {r[:cap]}" for r in (z.get("res") or [])]
        else:
            out.append(f"Reply: {(z.get('text') or '').strip()[:cap]}")
    t = "\n".join(out) if out else "Reply: "
    return t if len(t) <= 3000 else t[:2000] + "\n... (cut) ...\n" + t[-1000:]   # at most 3,000 characters (the scoring context is 16k)


def short_system(p, names):
    """MT-SEL: BFCL's system prompt with the json docs of only the functions in `names` (the ones the turn's rollouts call), then the
    names of the others; the full docs run to ~11k tokens"""
    s = p["system"]
    i = s.index("Here is a list of functions in json format")
    fl = json.loads(s[s.index("[", i):])
    keep = [f for f in fl if f["name"] in names]
    rest = [f["name"] for f in fl if f["name"] not in names]
    return (s[:i] + "Here are the functions in json format that the responses below call.\n" + json.dumps(keep, indent=1)
            + (f"\n\nOther available functions: {', '.join(rest)}." if rest else ""))


def main_sel_build():
    """addendum MT-SEL (--sel-build): the turn-0 rollouts of the arms SEL_ARMS of every model, each graded on its own (BFCL's per-turn
    check from the turn's start: end state and, for a non-empty ground truth, its execution results) -> $POC_DATA/bfcl/mt_sel_items.jsonl
    (per item: the shortened system prompt, the turn-0 request), results/conf/mt_sel_pool.jsonl (per item: every distinct rendered
    rollout, right, its sources), results/conf/mt_sel_rows.jsonl (per model, item and seed: N, the peer's N, T, the next seed's T, E, F as
    (text, right, output tokens, visible failure)) and the scoring requests results/conf/sel_req_mt_h<half>.jsonl (sset mt; half =
    crc32 of the scenario index mod 2: an item's three categories share a scenario)"""
    import hashlib, zlib
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    R = {(m, a): rows(m, a) for m in SEL_MODELS for a in SEL_ARMS}
    ids = sorted(i for i in P if all(i in R[(m, a)][s] for m in SEL_MODELS for a in SEL_ARMS for s in (1, 2, 3)))
    print(f"MT-SEL build: {len(ids)} of {len(P)} items have every model x arm x seed", flush=True)
    key = lambda i, t: hashlib.sha1(json.dumps(["tc", "mt", i, "sel", t]).encode()).hexdigest()[:20]   # lcm_shift.rv_key
    half = lambda i: zlib.crc32(i.rsplit("_", 1)[1].encode()) % 2
    pool, out, req, items = {}, [], {0: {}, 1: {}}, []
    for i in ids:
        p = P[i]; gt = p["ground_truth"][0]
        gi, gres = run(p, [gt] if gt else [], "sgt")
        memo, cand = {}, {}

        def grade(m, a, s):
            x = R[(m, a)][s][i]; t0 = x["turns"][0] if x["turns"] else []
            st = [z["calls"] for z in t0 if z["calls"]]
            txt = render(t0)
            if txt not in memo:
                ai, ares = run(p, st, f"sr{len(memo)}")   # a fresh name per run: BFCL keeps instances by name
                ok = same(ai, gi) and not (x["force_quit"] and len(x["turns"]) == 1)
                if ok and gt:
                    ok = bool(st) and response_checker(ares, gres, 0)["valid"]
                memo[txt] = bool(ok)
            c = cand.setdefault(txt, {"right": memo[txt], "src": [], "calls": sorted({re.sub(r"\(.*", "", c) for z in st for c in z})})
            c["src"].append([m, a, s])
            return (txt, memo[txt], sum(z["tok"] for z in t0), any(any(z.get("err") or []) or z.get("loop") for z in t0))
        G = {(m, a, s): grade(m, a, s) for m in SEL_MODELS for a in SEL_ARMS for s in (1, 2, 3)}
        for m in SEL_MODELS:
            for s in (1, 2, 3):
                out.append({"model": m, "id": i, "seed": s, "half": half(i), "roll": {
                    "N": G[(m, "N", s)], "P": G[(SEL_PEER[m], "N", s)], "T": G[(m, "T", s)], "T2": G[(m, "T", s % 3 + 1)],
                    "E": G[(m, "E", s)], "F": G[(m, "F", s)]}})
        names = {n for c in cand.values() for n in c["calls"]}
        items.append({"id": i, "system": short_system(p, names), "user": p["turns"][0][-1]["content"], "half": half(i)})
        pool[i] = cand
        for t in cand:
            h = key(i, t)
            req[half(i)][h] = {"h": h, "task": "tc", "sset": "mt", "id": i, "kind": "sel", "text": t}
    PD = os.path.dirname(DATA)
    with open(f"{PD}/mt_sel_items.jsonl", "w") as f:
        for x in items:
            f.write(json.dumps(x) + "\n")
    for h in (0, 1):
        with open(f"{PD}/mt_sel_ids_h{h}.txt", "w") as f:
            f.write("\n".join(x["id"] for x in items if x["half"] == h) + "\n")
    C = os.path.join(ROOT, "results", "conf")
    with open(f"{C}/mt_sel_pool.jsonl", "w") as f:
        for i, cand in pool.items():
            f.write(json.dumps({"id": i, "half": half(i), "cands": cand}) + "\n")
    with open(f"{C}/mt_sel_rows.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    for h in (0, 1):
        with open(f"{C}/sel_req_mt_h{h}.jsonl", "w") as f:
            for r in req[h].values():
                f.write(json.dumps(r) + "\n")
    mixed = {h: sum(1 for i, c in pool.items() if half(i) == h and any(v["right"] for v in c.values()) and not all(v["right"] for v in c.values()))
             for h in (0, 1)}
    print(f"MT-SEL build: {len(items)} items (half 0 {sum(x['half'] == 0 for x in items)}, half 1 {sum(x['half'] == 1 for x in items)}); "
          f"distinct rollouts {sum(len(c) for c in pool.values())}; items with a right and a wrong rollout {mixed}; scoring requests "
          f"{len(req[0])} / {len(req[1])}", flush=True)


if __name__ == "__main__":
    if "--sel-build" in sys.argv:
        main_sel_build()
    else:
        main()
