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


def short_system_fc(p, names):
    """MT-FC: as short_system, for an item whose functions are tools"""
    fl = [t["function"] for t in p["tools"]]
    keep = [f for f in fl if f["name"] in names]
    rest = [f["name"] for f in fl if f["name"] not in names]
    return ("You judge a function-calling turn. Here are the functions in json format that the responses below call.\n" + json.dumps(keep, indent=1)
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


def turn_context(p, k):
    """MT-SO: the verifier's request at turn k — turn 0: the request (MT-SEL's items); later: the earlier requests, then the current one"""
    if k == 0:
        return p["turns"][0][-1]["content"]
    prev = "\n".join(f"{j + 1}. {p['turns'][j][-1]['content']}" for j in range(k))
    return f"Earlier requests in this conversation (already handled):\n{prev}\n\nCurrent request: {p['turns'][k][-1]['content']}"


def turn_track(p, x, name):
    """MT-SO: the first wrong turn of trajectory row x (len(ground truth) when none), turn by turn as BFCL's multi_turn_checker: a turn
    with a non-empty ground truth needs a non-empty answer, every instance's state equal to the ground truth's and the turn's ground-truth
    execution results among all results so far; a turn with an empty ground truth must leave the state as the ground truth's (as MT-SEL's
    turn-0 labels; BFCL sees a change at the next turn's state check); a force-quit turn is wrong"""
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import state_checker
    cfg, cls, gts = p["initial_config"], p["involved_classes"], p["ground_truth"]
    ex = lambda c, nm: U.execute_multi_turn_func_call(c, cfg, cls, nm, p["id"], long_context=False, is_evaL_run=True)
    allres = []
    try:
        for k, gt in enumerate(gts):
            if k >= len(x["turns"]):
                return k
            st = [z["calls"] for z in x["turns"][k] if z["calls"]]
            for c in st:
                allres += ex(c, name)[0]
            mi = ex([], name)[1]
            gres, gi = ex(gt, name + "_gt")
            if (x["force_quit"] and k == len(x["turns"]) - 1) or (gt and (not st or U.is_empty_execute_response(st))):
                return k
            if not state_checker(mi, gi)["valid"] or (gt and not response_checker(allres, gres, k)["valid"]):
                return k
        return len(gts)
    finally:
        for nm in (name, name + "_gt"):
            for c in cls:
                U.__dict__.pop(re.sub(r"[-./:]", "_", f"{nm}_eval_{p['id']}_{c}_instance"), None)


def main_sel_build2():
    """addendum MT-SO (--sel-build2): MT-SEL's data plus every later turn. Each stored trajectory (SEL_MODELS x SEL_ARMS x seeds 1-3) is
    graded turn by turn (turn_track); at turn k >= 1 the trajectories still right through turn k-1 (their state is the ground truth's)
    give rollouts of that turn, right when the trajectory is still right after it. Request id <item>/t<k>, its context turn_context
    (the requests so far). Writes $POC_DATA/bfcl/mt_sel2_items.jsonl, mt_sel2_ids_h<half>.txt, results/conf/mt_sel2_pool.jsonl,
    results/conf/mt_sel2_rows.jsonl (turn 0: MT-SEL's rows; turn k: per model and seed, N, the peer's N, T (and the next seed's T) when
    those trajectories are all still right through turn k-1 — sets as the online choice sees them, but from different histories) and
    results/conf/sel_req_mt2_h<half>.jsonl (sset mt2, every text of the half, turn 0 included). Also prints how often the trajectory's
    last turn_track agrees with BFCL's grade (results/tc/mt_grades_*)."""
    import hashlib, zlib
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    R = {(m, a): rows(m, a) for m in SEL_MODELS for a in SEL_ARMS}
    C = os.path.join(ROOT, "results", "conf")
    PD = os.path.dirname(DATA)
    it0 = {x["id"]: x for x in map(json.loads, open(f"{PD}/mt_sel_items.jsonl"))}
    pool0 = {r["id"]: r for r in map(json.loads, open(f"{C}/mt_sel_pool.jsonl"))}
    rows0 = [json.loads(l) for l in open(f"{C}/mt_sel_rows.jsonl")]
    ids = sorted(it0)
    key = lambda i, t: hashlib.sha1(json.dumps(["tc", "mt2", i, "sel", t]).encode()).hexdigest()[:20]   # lcm_shift.rv_key
    half = lambda i: zlib.crc32(i.split("/")[0].rsplit("_", 1)[1].encode()) % 2
    G = {(m, a, s): json.load(open(f"{RES}/mt_grades_{m}_{a}_s{s}.json")) for m in SEL_MODELS for a in SEL_ARMS for s in (1, 2, 3)}
    items = [dict(x, turn=0) for x in it0.values()]
    pool = {i: dict(pool0[i], turn=0) for i in ids}
    out = [dict(r, turn=0) for r in rows0]
    agree, conflict, n = Counter(), 0, 0
    for i in ids:
        p = P[i]
        F = {}
        for m in SEL_MODELS:
            for a in SEL_ARMS:
                for s in (1, 2, 3):
                    x = R[(m, a)][s][i]
                    F[(m, a, s)] = turn_track(p, x, f"tt{n}"); n += 1
                    agree[(F[(m, a, s)] == len(p["ground_truth"])) == G[(m, a, s)][i]["ok"]] += 1
        for k in range(1, len(p["ground_truth"])):
            cand, roll = {}, {}
            for (m, a, s), f in F.items():
                x = R[(m, a)][s][i]
                if f < k or k >= len(x["turns"]):
                    continue
                tk = x["turns"][k]
                txt = render(tk)
                ok = f > k
                st = [z["calls"] for z in tk if z["calls"]]
                c = cand.setdefault(txt, {"right": ok, "src": [], "calls": sorted({re.sub(r"\(.*", "", c) for z in st for c in z})})
                conflict += c["right"] != ok
                c["src"].append([m, a, s])
                roll[(m, a, s)] = (txt, c["right"], sum(z["tok"] for z in tk), any(any(z.get("err") or []) or z.get("loop") for z in tk))
            if not cand:
                continue
            j = f"{i}/t{k}"
            names = {nm for c in cand.values() for nm in c["calls"]}
            items.append({"id": j, "system": short_system(p, names), "user": turn_context(p, k), "half": half(i), "turn": k})
            pool[j] = {"id": j, "half": half(i), "cands": cand, "turn": k}
            for m in SEL_MODELS:
                for s in (1, 2, 3):
                    q = {"N": (m, "N", s), "P": (SEL_PEER[m], "N", s), "T": (m, "T", s), "T2": (m, "T", s % 3 + 1)}
                    if all(q[r] in roll for r in ("N", "P", "T")):
                        out.append({"model": m, "id": j, "seed": s, "half": half(i), "turn": k,
                                    "roll": {r: roll[v] for r, v in q.items() if v in roll}})
    req = {0: {}, 1: {}}
    for j, r in pool.items():
        for t in r["cands"]:
            h = key(j, t)
            req[r["half"]][h] = {"h": h, "task": "tc", "sset": "mt2", "id": j, "kind": "sel", "text": t}
    with open(f"{PD}/mt_sel2_items.jsonl", "w") as f:
        for x in items:
            f.write(json.dumps(x) + "\n")
    for h in (0, 1):
        with open(f"{PD}/mt_sel2_ids_h{h}.txt", "w") as f:
            f.write("\n".join(x["id"] for x in items if x["half"] == h) + "\n")
        with open(f"{C}/sel_req_mt2_h{h}.jsonl", "w") as f:
            for r in req[h].values():
                f.write(json.dumps(r) + "\n")
    with open(f"{C}/mt_sel2_pool.jsonl", "w") as f:
        for r in pool.values():
            f.write(json.dumps(r) + "\n")
    with open(f"{C}/mt_sel2_rows.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    mixed = lambda r: any(v["right"] for v in r["cands"].values()) and not all(v["right"] for v in r["cands"].values())
    print(f"MT-SO build: trajectory grades, turn_track all right == BFCL's grade {dict(agree)}; rollouts whose rendered text another "
          f"rollout shares with the other label {conflict}", flush=True)
    for k in sorted({r["turn"] for r in pool.values()}):
        rs = [r for r in pool.values() if r["turn"] == k]
        print(f"  turn {k}: {len(rs)} requests, {sum(len(r['cands']) for r in rs)} distinct rollouts, with a right and a wrong "
              f"{sum(mixed(r) for r in rs)} (half 0 {sum(mixed(r) for r in rs if r['half'] == 0)}); pseudo-sets "
              f"{sum(1 for r in out if r['turn'] == k)}", flush=True)
    print(f"MT-SO build: scoring requests {len(req[0])} / {len(req[1])}", flush=True)


def plain(o, depth=0, seen=None):
    """MT-SD: an instance attribute as plain data (dicts, lists, scalars), object attributes as dicts, parent links skipped, depth <= 8"""
    seen = set() if seen is None else seen
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    if depth > 8 or id(o) in seen:
        return "..."
    seen = seen | {id(o)}
    if isinstance(o, dict):
        return {str(k): plain(v, depth + 1, seen) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [plain(v, depth + 1, seen) for v in (sorted(o, key=str) if isinstance(o, set) else o)]
    if hasattr(o, "__dict__"):
        return {k: plain(v, depth + 1, seen) for k, v in vars(o).items() if not k.startswith("_") and k != "parent"}
    return repr(o)[:200]


def state_diff(a, b, path="", out=None, cap=40):
    """MT-SD: added (+), removed (-) and changed (~) paths between two plain states, values cut at 100 characters, at most `cap` lines"""
    out = [] if out is None else out
    sh = lambda v: json.dumps(v, default=str)[:100]
    if len(out) >= cap or a == b:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if len(out) >= cap:
                break
            if k not in a:
                out.append(f"+ {path}{k}: {sh(b[k])}")
            elif k not in b:
                out.append(f"- {path}{k}")
            elif a[k] != b[k]:
                state_diff(a[k], b[k], f"{path}{k}.", out, cap)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) == len(b):
            for j, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    state_diff(x, y, f"{path}{j}.", out, cap)
        else:
            new = [y for y in b if y not in a]; gone = [x for x in a if x not in b]
            out += [f"+ {path[:-1]}[]: {sh(y)}" for y in new][:max(0, cap - len(out))]
            out += [f"- {path[:-1]}[]: {sh(x)}" for x in gone][:max(0, cap - len(out))]
    else:
        out.append(f"~ {path[:-1]}: {sh(a)} -> {sh(b)}")
    return out


def main_state_diff():
    """addendum MT-SD (--state-diff): every stored trajectory (SEL_MODELS x SEL_ARMS x seeds 1-3) replayed turn by turn on BFCL's instances,
    each turn's state change (state_diff of every involved instance's public attributes); every pseudo-set rollout text gets the change
    of its first source trajectory's turn. Writes results/conf/mt_sd_diff.jsonl {id, text hash, diff} and the variant files with the
    text 'render + State changes:' — $POC_DATA/bfcl/mt_sd_items.jsonl (= mt_sel2's), results/conf/mt_sd_pool.jsonl, mt_sd_rows.jsonl,
    sel_req_mtsd_h<half>.jsonl (sset mt2)."""
    import hashlib
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    R = {(m, a): rows(m, a) for m in SEL_MODELS for a in SEL_ARMS}
    C = os.path.join(ROOT, "results", "conf")
    PD = os.path.dirname(DATA)
    key = lambda i, t: hashlib.sha1(json.dumps(["tc", "mt2", i, "sel", t]).encode()).hexdigest()[:20]
    pool = [json.loads(l) for l in open(f"{C}/mt_sel2_pool.jsonl")]
    need = {}
    for r in pool:
        i = r["id"].split("/")[0]
        for t, c in r["cands"].items():
            m, a, s = c["src"][0]
            need.setdefault((m, a, s, i), set()).add(r["turn"])
    D, n = {}, 0
    for (m, a, s, i), turns in need.items():
        p, x = P[i], R[(m, a)][s][i]
        cfg, cls = p["initial_config"], p["involved_classes"]
        name = f"sd{n}"; n += 1
        ex = lambda c: U.execute_multi_turn_func_call(c, cfg, cls, name, p["id"], long_context=False, is_evaL_run=True)
        inst = lambda: {c: plain(U.__dict__.get(re.sub(r"[-./:]", "_", f"{name}_eval_{p['id']}_{c}_instance"))) for c in cls}
        try:
            ex([])
            for k in range(max(turns) + 1):
                if k >= len(x["turns"]):
                    break
                before = inst()
                for z in x["turns"][k]:
                    if z["calls"]:
                        ex(z["calls"])
                if k in turns:
                    D[(m, a, s, i, k)] = state_diff(before, inst()) or ["(no change)"]
        except Exception as e:
            print(f"  replay {m} {a} {s} {i}: {type(e).__name__}", flush=True)
        finally:
            for c in cls:
                U.__dict__.pop(re.sub(r"[-./:]", "_", f"{name}_eval_{p['id']}_{c}_instance"), None)
    nt = lambda t, d: t + "\nState changes:\n" + "\n".join(d)
    newtext = {}
    with open(f"{C}/mt_sd_diff.jsonl", "w") as f:
        for r in pool:
            i = r["id"].split("/")[0]
            for t, c in r["cands"].items():
                m, a, s = c["src"][0]
                d = D.get((m, a, s, i, r["turn"]), ["(unknown)"])
                newtext[(r["id"], t)] = nt(t, d)
                f.write(json.dumps({"id": r["id"], "h": key(r["id"], t), "diff": d}) + "\n")
    with open(f"{C}/mt_sd_pool.jsonl", "w") as f:
        for r in pool:
            f.write(json.dumps(dict(r, cands={newtext[(r["id"], t)]: c for t, c in r["cands"].items()})) + "\n")
    with open(f"{C}/mt_sd_rows.jsonl", "w") as f:
        for l in open(f"{C}/mt_sel2_rows.jsonl"):
            r = json.loads(l)
            r["roll"] = {k: [newtext.get((r["id"], v[0]), v[0])] + v[1:] for k, v in r["roll"].items()}
            f.write(json.dumps(r) + "\n")
    import shutil
    shutil.copy(f"{PD}/mt_sel2_items.jsonl", f"{PD}/mt_sd_items.jsonl")
    for h in (0, 1):
        with open(f"{C}/sel_req_mtsd_h{h}.jsonl", "w") as f:
            for l in open(f"{C}/sel_req_mt2_h{h}.jsonl"):
                q = json.loads(l)
                t2 = newtext.get((q["id"], q["text"]))
                if t2 is None:
                    continue
                f.write(json.dumps(dict(q, h=key(q["id"], t2), text=t2)) + "\n")
    print(f"MT-SD: {len(need)} trajectories replayed, {len(D)} turn changes, {len(newtext)} rollout texts", flush=True)


JUDGE = """{context}

Here are {n} candidate responses to the latest request. Each is shown as the function calls it made, their results, and its final
reply:

{cands}

Which response correctly handles the latest request? Reply with the letter only."""


def main_judge():
    """addendum MT-JG (--judge <tag> [--max_tokens N]): on every pseudo-set (results/conf/mt_sel2_rows.jsonl) with a right and a wrong
    distinct rollout, the generator server's model, thinking, reads the short system prompt (the set's functions), the turn context and
    the distinct rollouts (render, labelled A/B/C in a seeded random order) and names one -> results/conf/mt_judge_<tag>.jsonl"""
    import random, zlib
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from llm import chat_msgs
    tag = sys.argv[sys.argv.index("--judge") + 1]
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 4096
    C = os.path.join(ROOT, "results", "conf")
    PD = os.path.dirname(DATA)
    items = {x["id"]: x for x in map(json.loads, open(f"{PD}/mt_sel2_items.jsonl"))}
    rows = [r for r in map(json.loads, open(f"{C}/mt_sel2_rows.jsonl"))
            if len({r["roll"][k][1] for k in ("N", "P", "T")}) == 2]
    out = f"{C}/mt_judge_{tag}.jsonl"
    done = {(r["model"], r["id"], r["seed"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [r for r in rows if (r["model"], r["id"], r["seed"]) not in done]
    print(f"MT-JG {tag}: {len(todo)} of {len(rows)} mixed sets", flush=True)

    def one(r):
        T = list(dict.fromkeys(r["roll"][k][0] for k in ("N", "P", "T")))
        lab = {r["roll"][k][0]: r["roll"][k][1] for k in ("N", "P", "T")}
        random.Random(zlib.crc32(f"{r['model']}{r['id']}{r['seed']}".encode())).shuffle(T)
        L = "ABC"[:len(T)]
        it = items[r["id"]]
        msgs = [{"role": "system", "content": it["system"]},
                {"role": "user", "content": JUDGE.format(context=it["user"], n=len(T),
                                                         cands="\n\n".join(f"Response {L[j]}:\n{t}" for j, t in enumerate(T)))}]
        a = chat_msgs(msgs, think=True, max_tokens=mt, temperature=0.6)
        m = re.findall(r"\b([A-C])\b", a["text"])
        pick = m[-1] if m and m[-1] in L else None
        return {"model": r["model"], "id": r["id"], "seed": r["seed"], "half": r["half"], "turn": r["turn"], "pick": pick,
                "right": lab[T[L.index(pick)]] if pick else None, "order": [lab[t] for t in T], "out_tokens": a["out_tokens"],
                "finish": a["finish"], "text": a["text"][-300:]}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for fu in as_completed([ex.submit(one, r) for r in todo]):
            try:
                f.write(json.dumps(fu.result()) + "\n"); f.flush()
            except Exception as e:
                print(f"  failed: {type(e).__name__}: {str(e)[:200]}", flush=True)


def main_rn():
    """addendum MT-RN (--rn <tag>): the trained quick turn's trajectories (rows of <tag>, arm N) against Qwen3-8B's pseudo-sets: on a set of
    the same item, seed and turn where the trajectory is right through k-1, the oracle of {N, P, T} with and without its turn"""
    from collections import defaultdict
    import random
    tag = sys.argv[sys.argv.index("--rn") + 1]
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    X = rows(tag, "N")
    C = os.path.join(ROOT, "results", "conf")
    F, n = {}, 0
    tg = lambda k: str(k) if k < 3 else "3+"
    A = defaultdict(lambda: [0, 0, 0, 0, 0])   # turn group: sets, oracle of three, oracle with the trained turn, the trained turn right, oracle with it replacing N
    D = defaultdict(list)
    for r in map(json.loads, open(f"{C}/mt_sel2_rows.jsonl")):
        if r["model"] != "q8b":
            continue
        i, k, s = r["id"].split("/")[0], r["turn"], r["seed"]
        x = X[s].get(i)
        if x is None:
            continue
        if (i, s) not in F:
            F[(i, s)] = turn_track(P[i], x, f"rn{n}"); n += 1
        f = F[(i, s)]
        if f < k or k >= len(x["turns"]):
            continue
        o3 = any(r["roll"][j][1] for j in ("N", "P", "T"))
        ok = f > k
        a = A[tg(k)]
        a[0] += 1; a[1] += o3; a[2] += o3 or ok; a[3] += ok; a[4] += ok or r["roll"]["P"][1] or r["roll"]["T"][1]
        D[i].append(float(ok and not o3))
        A[(i.rsplit("_", 1)[0], tg(k))][0] += 1; A[(i.rsplit("_", 1)[0], tg(k))][2] += float(ok and not o3)
    for g in ("0", "1", "2", "3+"):
        a = A[g]
        print(f"turn {g}: {a[0]} sets; oracle N,P,T {100 * a[1] / a[0]:.1f}%; with the trained turn {100 * a[2] / a[0]:.1f}%; the trained turn alone {100 * a[3] / a[0]:.1f}%", flush=True)
    for c in sorted({k[0] for k in A if isinstance(k, tuple)}):
        print(f"  {c}: rescued at turn 0 {100 * A[(c, '0')][2] / max(1, A[(c, '0')][0]):.1f}% of sets", flush=True)
    import math
    dist = Counter(len(p["turns"]) for p in P.values()); nn = sum(dist.values())
    conv = lambda j: sum(w / nn * math.prod(A[tg(k)][j] / A[tg(k)][0] for k in range(K)) for K, w in dist.items())
    print(f"compounding, conversation: oracle {100 * conv(1):.1f}% -> with the trained turn {100 * conv(2):.1f}%; at the verifier's 0.56 share "
          f"{100 * 0.56 * (conv(2) - conv(1)):+.1f} points", flush=True)
    print(f"compounding, the trained turn replacing N: oracle {100 * conv(1):.1f}% -> {100 * conv(4):.1f}%; at the verifier's 0.56 share "
          f"{100 * 0.56 * (conv(4) - conv(1)):+.1f} points (MT-RF-P2: bar 3)", flush=True)
    ids = sorted(D); rng = random.Random(0)
    per = {i: sum(D[i]) / len(D[i]) for i in ids}
    bs = sorted(sum(per[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(2000))
    m = sum(per.values()) / len(ids)
    print(f"*** MT-RN-P2: delta oracle per turn {100 * m:+.2f} [{100 * bs[50]:+.2f}, {100 * bs[1949]:+.2f}] points (bar 1.9, lower bound > 0): "
          f"{'holds' if bs[50] > 0 and 100 * m >= 1.9 else 'refuted'}", flush=True)


def main_rf_build():
    """addendum MT-RF (--rf-build): per request (item, turn k) the right rollouts of mt_sel2's pool, each as a list of rows: the conversation
    so far (the source trajectory's right history, tool results replayed in full) -> the step's text; a step whose calls returned an
    error is no target. Writes $POC_DATA/bfcl/mt_rf_h<half>.jsonl, one row per rollout: {req, item, steps: [{msgs, target}]} (msgs
    without the system prompt)."""
    P = {p["id"]: p for p in map(json.loads, open(DATA))}
    R = {(m, a): rows(m, a) for m in SEL_MODELS for a in SEL_ARMS}
    C = os.path.join(ROOT, "results", "conf")
    PD = os.path.dirname(DATA)
    need = {}
    pool = [json.loads(l) for l in open(f"{C}/mt_sel2_pool.jsonl")]
    for r in pool:
        i = r["id"].split("/")[0]
        for t, c in r["cands"].items():
            if c["right"]:
                m, a, s = c["src"][0]
                need.setdefault((m, a, s, i), []).append((r["id"], r["turn"], r["half"]))
    out = {0: [], 1: []}
    for n, ((m, a, s, i), reqs) in enumerate(need.items()):
        p, x = P[i], R[(m, a)][s][i]
        cfg, cls = p["initial_config"], p["involved_classes"]
        name = f"rf{n}"
        ex = lambda c: U.execute_multi_turn_func_call(c, cfg, cls, name, p["id"], long_context=False)
        want = {k: (j, h) for j, k, h in reqs}
        hist = []
        try:
            ex([])
            for k in range(max(want) + 1):
                if k >= len(x["turns"]) or k >= len(p["turns"]):
                    break
                hist += p["turns"][k]
                rowsk = []
                for z in x["turns"][k]:
                    if z["calls"]:
                        text = "[" + ", ".join(z["calls"]) + "]"
                        if not any(z.get("err") or []):
                            rowsk.append({"msgs": list(hist), "target": text})
                        res, _ = ex(z["calls"])
                        hist.append({"role": "assistant", "content": text})
                        hist += [{"role": "tool", "name": c, "content": r_} for c, r_ in zip(z["calls"], res)]
                    else:
                        text = (z.get("text") or "").strip()
                        if text:
                            rowsk.append({"msgs": list(hist), "target": text})
                            hist.append({"role": "assistant", "content": text})
                if k in want and rowsk:
                    j, h = want[k]
                    out[h].append({"req": j, "item": i, "steps": rowsk})
        except Exception as e:
            print(f"  {m} {a} {s} {i}: {type(e).__name__}: {str(e)[:100]}", flush=True)
        finally:
            for c in cls:
                U.__dict__.pop(re.sub(r"[-./:]", "_", f"{name}_{p['id']}_{c}_instance"), None)
    for h in (0, 1):
        with open(f"{PD}/mt_rf_h{h}.jsonl", "w") as f:
            for r in out[h]:
                f.write(json.dumps(r) + "\n")
        print(f"MT-RF half {h}: {len(out[h])} right rollouts of {len({r['req'] for r in out[h]})} requests, "
              f"{sum(len(r['steps']) for r in out[h])} rows", flush=True)


if __name__ == "__main__":
    if "--rf-build" in sys.argv:
        main_rf_build()
    elif "--rn" in sys.argv:
        main_rn()
    elif "--judge" in sys.argv:
        main_judge()
    elif "--state-diff" in sys.argv:
        main_state_diff()
    elif "--sel-build" in sys.argv:
        main_sel_build()
    elif "--sel-build2" in sys.argv:
        main_sel_build2()
    else:
        main()
