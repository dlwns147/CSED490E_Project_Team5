"""PROV scorer (PREREG_DIFF): label-free failure flag of a native-tool attempt = the final answer was never printed by one of its tool runs, or no answer / call cap. usage: python tir_prov.py comp | euler eulert"""
import itertools, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tir_native as T
import tir_score as S
R = S.R; U = S.U; L = S.L


def rows(st, eff, seed):
    for tag in ("N", ""):
        z = L(f"{R}/tir_{st}_{eff}{tag}_s{seed}.jsonl")
        if z:
            break
    if not z:
        return None
    z = S.regrade(st, z)
    for r in z.values():
        pv = r["prov"] if "prov" in r else T.provenance(r)      # seed 1 rows: from tool outputs cut at 300 characters
        r["flag"] = not pv or r["finish"] != "stop"
    return z


def main(st):
    Z = {s: rows(st, "medium", s) for s in [int(x) for x in os.environ.get("PROV_SEEDS", "1,2,3").split(",")]}; Z = {s: z for s, z in Z.items() if z}; H = rows(st, "high", 1)
    ids = sorted(set.intersection(*(set(z) for z in Z.values()))); ok = lambda r: float(bool(r["correct"])); tk = lambda r: r["out_tokens"]
    print(f"== {st}: {len(ids)} problems, medium seeds {sorted(Z)}" + (", high seed 1" if H else ""))
    for s, z in Z.items():
        fl = [z[i] for i in ids if z[i]["flag"]]; un = [z[i] for i in ids if not z[i]["flag"]]
        print(f"   seed {s}: flagged {len(fl)} of {len(ids)}, right among flagged {sum(ok(r) for r in fl):.0f} (precision of 'wrong' {100*(1-sum(ok(r) for r in fl)/max(1,len(fl))):.0f}%), right among not flagged {sum(ok(r) for r in un):.0f} of {len(un)} ({100*sum(ok(r) for r in un)/max(1,len(un)):.0f}%); tokens flagged {sum(map(tk, fl))/max(1,len(fl))/1000:.1f}k, not {sum(map(tk, un))/max(1,len(un))/1000:.1f}k")
    A = {"ONE": {}, "PROV-HIGH": {}, "HIGH-TOOL": {}, "PROV2": {}, "MAJ3": {}, "RAND2": {}}
    for i in ids:
        A["ONE"][i] = [(ok(z[i]), tk(z[i])) for z in Z.values()]
        if H and i in H:
            A["HIGH-TOOL"][i] = [(ok(H[i]), tk(H[i]))]
            A["PROV-HIGH"][i] = [(ok(z[i]), tk(z[i])) if not z[i]["flag"] else ((ok(H[i]) if not H[i]["flag"] else ok(z[i])) if z[i]["flag"] else 0, tk(z[i]) + tk(H[i])) for z in Z.values()]
        if len(Z) >= 2:
            A["PROV2"][i] = [(ok(Z[a][i]), tk(Z[a][i])) if not Z[a][i]["flag"] else ((ok(Z[b][i]) if not Z[b][i]["flag"] else ok(Z[a][i])), tk(Z[a][i]) + tk(Z[b][i])) for a, b in itertools.permutations(Z, 2)]
    if len(Z) >= 2:
        q = sum(Z[a][i]["flag"] for a in Z for i in ids) / (len(Z) * len(ids))        # RAND2: a second attempt on a random share q of the problems; its answer replaces the first's when not flagged (same rule), expectation over the draw
        for i in ids:
            A["RAND2"][i] = [((1 - q) * ok(Z[a][i]) + q * (ok(Z[b][i]) if not Z[b][i]["flag"] else ok(Z[a][i])), tk(Z[a][i]) + q * tk(Z[b][i])) for a, b in itertools.permutations(Z, 2)]
    if len(Z) == 3:
        import ma_effort as M
        import run_compute as RC
        for i in ids:
            v = []
            for p in itertools.permutations(Z):
                a = [RC.norm(M.ans(Z[s][i]["final"]) or "") for s in p]; k = next((j for j in range(3) if a[j] and a.count(a[j]) >= 2), 0)
                v.append((ok(Z[p[k]][i]), sum(tk(Z[s][i]) for s in p)))
            A["MAJ3"][i] = v
    A = {k: {i: (sum(a for a, _ in v) / len(v), sum(t for _, t in v) / len(v)) for i, v in x.items()} for k, x in A.items() if x}
    for k, x in A.items():
        print(f"   {k:10s} {100*sum(a for a, _ in x.values())/len(x):.1f}% @ {sum(t for _, t in x.values())/len(x)/1000:.2f}k utility {sum(U(*v) for v in x.values())/len(x):.2f}")
    for a, b in (("PROV2", "ONE"), ("PROV2", "MAJ3"), ("PROV2", "RAND2"), ("PROV-HIGH", "ONE"), ("PROV-HIGH", "HIGH-TOOL"), ("PROV-HIGH", "PROV2"), ("MAJ3", "ONE")):
        if a in A and b in A:
            print(f"   {a} − {b}: accuracy {S.ci([100*(A[a][i][0]-A[b][i][0]) for i in ids])} ktok {S.ci([(A[a][i][1]-A[b][i][1])/1000 for i in ids])} utility {S.ci([U(*A[a][i])-U(*A[b][i]) for i in ids])}")
    return ids, A


if __name__ == "__main__":
    out = [main(s) for s in sys.argv[1:]]
    if len(out) > 1:
        print("== pooled")
        for a, b in (("PROV2", "ONE"), ("PROV2", "MAJ3"), ("PROV2", "RAND2"), ("PROV-HIGH", "ONE"), ("PROV-HIGH", "HIGH-TOOL"), ("PROV-HIGH", "PROV2")):
            if all(a in A and b in A for _, A in out):
                d = [U(*A[a][i]) - U(*A[b][i]) for ids, A in out for i in ids]; e = [100 * (A[a][i][0] - A[b][i][0]) for ids, A in out for i in ids]
                print(f"   {a} − {b}: accuracy {S.ci(e)} utility {S.ci(d)}")
