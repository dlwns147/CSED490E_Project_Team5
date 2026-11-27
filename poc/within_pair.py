"""Pooled vs within-pair discrimination of a free signal (generated tokens) across sets, from stored tool rows (2026-11-27); run inside the gs15 container. A pooled AUROC compares attempts at different problems (difficulty); the within-pair rate compares two attempts at the same problem, the quantity selection depends on."""
import json, glob, itertools, collections, sys
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import ma_effort as M, run_compute as RC
D = "/NAS/SJ/POSTECH/nlp/results/x44/"
gold = {p["id"]: p["answer"] for st in ("euler", "eulert") for p in RC.problems(st)}
def ok_e(r): a = M.ans(r.get("final", "")) or ""; return bool(a) and RC.norm(a) == RC.norm(gold[r["id"]])
SETS = {"Project Euler (tool, mediumN s1-5)": ([f"{D}tir_euler_mediumN_s{s}.jsonl" for s in range(1, 6)] + [f"{D}tir_eulert_mediumN_s{s}.jsonl" for s in range(1, 6)], ok_e),
        "competition (tool, mediumN s2-3 + medium s1)": ([f"{D}tir_comp_mediumN_s2.jsonl", f"{D}tir_comp_mediumN_s3.jsonl", f"{D}tir_comp_medium_s1.jsonl"], lambda r: bool(r.get("correct"))),
        "MathConstruct (OWN-E 120b s1-4)": ([f"{D}tirsub3_OWN_mcong_medium_s{s}.jsonl" for s in range(1, 5)], lambda r: bool(r.get("correct")))}
for name, (files, ok) in SETS.items():
    by = collections.defaultdict(list)
    for f in files:
        try:
            for l in open(f):
                r = json.loads(l); t = r.get("out_tokens_total", r.get("out_tokens", 0)); by[r["id"]].append((ok(r), t))
        except FileNotFoundError:
            pass
    allr = [x for v in by.values() for x in v]; P = [t for c, t in allr if c]; N = [t for c, t in allr if not c]
    pooled = sum((p < n) + 0.5 * (p == n) for p in P for n in N) / max(1, len(P) * len(N))
    w = m = 0
    for v in by.values():
        for (c1, t1), (c2, t2) in itertools.combinations(v, 2):
            if c1 != c2:
                m += 1; tr, tw = (t1, t2) if c1 else (t2, t1); w += (tr < tw) + 0.5 * (tr == tw)
    print(f"{name}: attempts {len(allr)}; pooled AUROC (fewer tokens = right) {pooled:.3f}; within-pair (one right, one wrong; {m} pairs) the right one is shorter {w/max(1,m):.3f}")
