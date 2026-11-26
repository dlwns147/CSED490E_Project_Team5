"""DISPUTE-E scorer with the corrected Project Euler reader (2026-11-26 20:0x UTC). The run-time grade of tir_dispute / tir_dispute2 used run_compute's
boxed+norm reader, which marks '9\\,936\\,352' and 'S(10^8)=33626723890930' wrong; every earlier Euler table was regraded by tir_score.regrade
(ma_effort.ans: digit grouping removed, value after the last '='). This scorer applies the same reader to both attempts, then reuses tir_dispute2.arms.
usage: python tir_dispute_score.py <prefix tirdis|tirdis2> <seedA> <seedB>"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_dispute2 as D2
import tir_score as S
import ma_effort as M
import run_compute as RC


def main(prefix, sa, sb):
    U = S.U; A = {}; D = {}; ch = 0
    for st in ("euler", "eulert"):
        p = f"{D2.R}/{prefix}_{st}_medium_s{sa}_{sb}.jsonl"
        if not os.path.exists(p):
            continue
        g = {q["id"]: q["answer"] for q in RC.problems(st)}; seen = set()
        for l in open(p):
            z = json.loads(l)
            if "error" in z or z["id"] in seen:
                continue
            seen.add(z["id"])
            for k in ("A", "B"):
                a = M.ans(z[k]["final"]) or ""; ok = bool(a) and RC.norm(a) == RC.norm(g[z["id"]]); ch += ok != bool(z[k]["correct"]); z[k]["correct"] = ok
            for k, v in D2.arms(z).items():
                A.setdefault(k, {})[(st, z["id"])] = (sum(a for a, _ in v) / len(v), sum(t for _, t in v) / len(v))
            D[(st, z["id"])] = z
    print(f"grades changed by the corrected reader: {ch} attempts")
    for lab, sts in (("euler", ("euler",)), ("eulert", ("eulert",)), ("pooled", ("euler", "eulert"))):
        ks = [k for k in A.get("ONE", {}) if k[0] in sts]
        if not ks:
            continue
        print(f"== {lab}: {len(ks)} problems, disputed {sum(D[k]['disputed'] for k in ks)}")
        for a in A:
            print(f"   {a:9s} {100*sum(A[a][k][0] for k in ks)/len(ks):.1f}% @ {sum(A[a][k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*A[a][k]) for k in ks)/len(ks):.2f}")
        one = sum(A['ONE'][k][0] for k in ks); orc = sum(A['ORACLE2'][k][0] for k in ks)
        print("   share captured: " + ", ".join(f"{a} {(sum(A[a][k][0] for k in ks)-one)/max(1e-9, orc-one):.2f}" for a in A if a not in ("ONE", "ORACLE2")))
        for a, b in (("DISPUTE", "JUDGE"), ("DISPUTE-P", "PROV2"), ("DISPUTE", "ONE"), ("JUDGE", "ONE"), ("PROV2", "ONE"), ("DISPUTE", "CONF-LOW"), ("DISPUTE", "CONF-TAIL"), ("CONF-LOW", "ONE"), ("CONF-TAIL", "ONE")):
            print(f"   {a} − {b}: accuracy {S.ci([100*(A[a][k][0]-A[b][k][0]) for k in ks])} ktok {S.ci([(A[a][k][1]-A[b][k][1])/1000 for k in ks])} utility {S.ci([U(*A[a][k])-U(*A[b][k]) for k in ks])}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
