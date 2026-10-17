"""N12 (results/PREREG_N10.md): agreement between tool conditions as the escalation gate. Offline on the N10 factorials.
A = first-attempt condition (geometry K8 toolbox / optimization full manual), B = cheap alternative (no helpers / BM25 snippets),
T = thinking. AGREE: accept A when A and B both pass the label-free check and give the same answer (geometry: the same output on the
given instance; optimization: both feasible with the same objective); else escalate to T; if T fails the check keep a check-passing
B, then A. Secondary: escalate to 3 samples + check (seeds 1-3 of A) instead of T.
usage: N10_PREFIX=S2_N10 python analyze_n12.py <seed> [geo|co ...]"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as A  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

PRE = os.environ.get("N10_PREFIX", "S2_N10")
sd = int(sys.argv[1]) if len(sys.argv) > 1 else 1
TAGS = {"geo": ("k8", "none", "think"), "co": ("doc", "rag3", "think")}


def rows_of(dom, tag):
    f = f"{A.RES}/geocross_{PRE}_geo_{tag}.jsonl" if dom == "geo" else f"{A.RES}/co_{PRE}_co_{tag}.jsonl"
    return {((r["task"], r["n"], r["inst"]) if dom == "geo" else r["key"]): r for r in map(json.loads, open(f))}


def geo_out(r):
    if not r.get("code"):
        return None
    k = "out|" + A.hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}".encode()).hexdigest()
    if k not in A.CACHE:
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        x = run_python(r["code"], render(r["task"], variants(r["task"], base_instance(r["task"], r["n"], rng), rng)["identity"])[1], timeout=10)
        A.CACHE[k] = (x.stdout.strip().split() or [""])[-1].lower() if x.status == "ok" else None
    return A.CACHE[k]


def main(dom):
    a_t, b_t, t_t = TAGS[dom]
    RA, RB, RT = rows_of(dom, f"{a_t}_s{sd}"), rows_of(dom, f"{b_t}_s{sd}"), rows_of(dom, f"{t_t}_s{sd}")
    keys = sorted(set(RA) & set(RB) & set(RT))
    chk = A.geo_check if dom == "geo" else A.co_check
    ok = (lambda r: r["class"] == "correct_all") if dom == "geo" else (lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0)
    ans = geo_out if dom == "geo" else (lambda r: r["value"] if r["status"] == "ok" and r["feasible"] else None)
    tok = lambda r: r.get("out_tokens") or 0
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(24) as ex:
        C = dict(zip([(x, k) for x in "ABT" for k in keys], ex.map(lambda j: chk({"A": RA, "B": RB, "T": RT}[j[0]][j[1]])[0], [(x, k) for x in "ABT" for k in keys])))
        if dom == "geo":
            list(ex.map(lambda j: geo_out({"A": RA, "B": RB}[j[0]][j[1]]), [(x, k) for x in "AB" for k in keys]))
    json.dump(A.CACHE, open(A.CACHE_F, "w"))
    acc = tk = esc = agree_wrong = 0
    for k in keys:
        a, b, t = RA[k], RB[k], RT[k]
        tk += tok(a) + tok(b)
        if C[("A", k)] and C[("B", k)] and ans(a) is not None and ans(a) == ans(b):
            acc += ok(a); agree_wrong += not ok(a)
            continue
        esc += 1; tk += tok(t)
        acc += ok(t) if C[("T", k)] else ok(b) if C[("B", k)] else ok(a) if C[("A", k)] else ok(t)
    n = len(keys)
    always = {nm: (100 * sum(ok(R[k]) for k in keys) / n, sum(tok(R[k]) for k in keys) / n) for nm, R in (("A (first)", RA), ("B (cheap)", RB), ("thinking", RT))}
    print(f"{PRE} {dom} seed {sd}: AGREE {100 * acc / n:.1f}% @ {tk / n:.0f} tokens (escalated {esc}/{n}; agreed but wrong {agree_wrong}) | "
          + " | ".join(f"always {nm} {a_:.1f}% @ {t_:.0f}" for nm, (a_, t_) in always.items()), flush=True)


if __name__ == "__main__":
    for d in sys.argv[2:] or ["geo", "co"]:
        main(d)
