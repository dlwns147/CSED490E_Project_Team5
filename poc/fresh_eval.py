"""Review item 1: evaluate selection on FRESH instances (never seen by the metamorphic check).
For each original instance, the candidate programs (3 tool-free samples) are selected with the metamorphic check on the GIVEN instance;
the chosen program is then scored on 5 fresh instances x 8 variants of the same task/size (seed keys `<task>-<n>-<i>-fresh<j>`, as in run_geo_mr.py).
Compared with: one random sample, and one sample with the task-matched predicates (stdpt / F_pt), scored on the same fresh instances.
usage: fresh_eval.py <model> <prefix> <base_arm> <pt_tag>"""
import collections, json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import types; sys.modules.setdefault("openai", types.SimpleNamespace(OpenAI=lambda **k: None))
import run_geo as G  # noqa: E402
from run_geo_mr import mr_check, run_out  # noqa: E402

R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
m, prefix, base_arm, pt_tag = sys.argv[1:5]
L = lambda t: {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f"{R}/geocross_{t}.jsonl"))}
S = [L(f"{prefix}{m}_{base_arm}_t07s{s}") for s in (1, 2, 3)]
PT = L(pt_tag)
keys = sorted(S[0])


def fresh_score(code, task, n, key):
    if not code:
        return 0.0
    ok = 0
    for j in range(5):
        rng = random.Random(f"{key}-fresh{j}")
        V = G.variants(task, G.base_instance(task, n, rng), rng)
        ok += all(run_out(code, task, x) == G.answer(task, x) for x in V.values())
    return ok / 5


def one(k):
    task, n, i = k; key = f"{task}-{n}-{i}"
    rng = random.Random(key); V = G.variants(task, G.base_instance(task, n, rng), rng)
    cands = []
    for j, s in enumerate(S):
        c = s[k].get("code")
        if c:
            b, bad = mr_check(c, task, V)
            if b is not None and not bad:
                cands.append((j, b))
    pick = None
    if cands:
        vote = collections.Counter(b for _, b in cands).most_common(1)[0][0]
        pick = next(j for j, b in cands if b == vote)
    singles = [fresh_score(s[k].get("code"), task, n, key) for s in S]
    return {"single": sum(singles) / 3, "mr": singles[pick] if pick is not None else 0.0,
            "pt": fresh_score(PT[k].get("code"), task, n, key) if k in PT else None}


with ThreadPoolExecutor(32) as ex:
    res = list(ex.map(one, keys))
mean = lambda f: 100 * sum(r[f] for r in res if r[f] is not None) / len([r for r in res if r[f] is not None])
print(f"{m}: FRESH-instance accuracy (5 fresh x 8 variants per original instance, n={len(res)}): one sample {mean('single'):.1f} | "
      f"3 samples + metamorphic check {mean('mr'):.1f} | one sample with task-matched predicates {mean('pt'):.1f}")
