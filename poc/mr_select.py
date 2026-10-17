"""S6 label-free selection among candidate programs (offline, CPU): for each instance, run every candidate program on the
metamorphic copies of the GIVEN instance (translate/rot90/mirror/permute/scale/1e9); keep candidates whose outputs satisfy all
relations; majority-vote the identity output among them and pick a program that produced it. Score = all-variants-correct
(the stored per_variant field, incl. degenerate + fresh-free variants as in run_geo_cross).
usage: mr_select.py <model> <seed> <arm1,arm2,...>"""
import json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc")
from run_geo import base_instance, variants  # noqa: E402
from run_geo_mr import mr_check  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
m, sd, arms = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
NOMR = len(sys.argv) > 4 and sys.argv[4] == "nomr"   # ablation: plain majority vote on the identity output (no metamorphic filter)
def _f(a):   # arm or arm@seed
    arm, _, s_ = a.partition("@")
    return f"{RES}/geocross_{os.environ.get('MR_PREFIX', 'geox')}{m}_{arm}_t07s{s_ or sd}.jsonl"
rows = {a: {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(_f(a)))} for a in arms}
keys = sorted(rows[arms[0]])


def pick(k):
    task, n, i = k
    rng = random.Random(f"{task}-{n}-{i}")
    V = variants(task, base_instance(task, n, rng), rng)
    cands = []
    for a in arms:
        r = rows[a].get(k)
        if r and r.get("code"):
            base, bad = mr_check(r["code"], task, V)
            if base is not None and (NOMR or not bad):
                cands.append((a, base))
    if not cands:
        return k, None, 0
    vote = Counter(b for _, b in cands).most_common(1)[0][0]
    a = next(a for a, b in cands if b == vote)
    return k, a, len(cands)


with ThreadPoolExecutor(32) as ex:
    res = list(ex.map(pick, keys))
ok = sum(rows[a][k]["class"] == "correct_all" for k, a, _ in res if a)
none = sum(1 for _, a, _ in res if a is None)
per_arm = {a: sum(rows[a][k]["class"] == "correct_all" for k in keys) for a in arms}
oracle = sum(any(rows[a][k]["class"] == "correct_all" for a in arms) for k in keys)
print(f"{m} s{sd} arms={arms} per-arm {per_arm} | MR-select {ok}/{len(keys)} (no consistent candidate: {none}) | oracle-any {oracle}",
      "| picked from", dict(Counter(a for _, a, _ in res if a)))
