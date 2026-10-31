"""CONT (docs/prereg/PREREG_CONT.md): policies built from poc/run_cont.py's thinks (one think per problem and seed, the program forced every
1,000 thinking tokens inside it, and the program at its end). Per problem and seed s (s2 = s % 3 + 1, s3 = s2 % 3 + 1, as HO-PA's retry):
  first(s)  the program cut at 2,000 thinking tokens of think s (the short think SB), or its end program if the think ends before;
  R0        restart = SB->T->T: first(s); on a failed check the end of think s2 (a fresh full think); on its failure the end of think s3;
  C0        continue: first(s); on a failed check think s continues to its end; on its failure the end of think s2 (fresh retry);
  RD(S)     R0 with the fresh think s2 checked at the cut points S: the first passing program is the answer, else its end program;
  CD(S)     C0 with think s checked at the points of S after 2,000 (where the think ended before 2,000: as RD);
  oracle    the first right program of think s (cut or end; the early-exit ceiling, not a policy).
Check = the program runs and prints a value (analyze_ho.ok_). Tokens = thinking tokens generated up to the stopping point + every program
generated (cut programs are branches off the same think; the continued think does not see them). S is chosen by greedy forward selection
of cut points (1,000 ... 15,000) maximising mean utility on one half of the problems (crc32(id) % 2) and scored on the other half
(cross-fitted; both halves pooled for the tests). Utility = accuracy - 0.5 x ktokens; paired 95% intervals over problems (seed means),
pooled over OptiBench's third, BWOR, LogiOR, OptMATH. Tests: CT-P1 RD - R0, CT-P2 C0 - R0, CT-P3 D = P(end of a fresh think right) -
P(end of the same think right) after a failed 2,000-token check, CT-P4 CD - RD, CT-P5 the better of RD / CD (the one with the higher
cross-fitted mean) - the stored default SB->T->T (analyze_hopa, rows of other runs).
usage: python analyze_cont.py [tag q8b]"""
import contextlib, io, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from analyze_ho3 import ci
    from analyze_hopa import BENCH, LAM, per_q, policies, same_word, word_rows
    from run_nlopt import RES, _rows

GRID = tuple(range(1000, 16000, 1000))
ok_ = lambda x: x["status"] == "ok" and x["pred"] not in (None, "NBS")


def load(tag, b):
    T = {s: {r["id"]: r for r in _rows(f"{RES}/cont_{tag}_{b}_s{s}.jsonl")} for s in (1, 2, 3)}
    ids = sorted(set.intersection(*(set(v) for v in T.values())))
    return T, ids


def run(t, S, start=0, spent=0):
    """think t checked at the cut points of S after `start` thinking tokens (already spent); -> (passes, right, tokens) of its answer"""
    cut = {p["at"]: p for p in t["probes"]}
    tok, at = spent, start
    for c in sorted(S):
        if c <= start or c not in cut:
            continue
        p = cut[c]; tok += c - at + p["tok"]; at = c
        if ok_(p):
            return True, p["right"], tok
    e = t["end"]
    return ok_(e), e["right"], tok + max(0, t["think_tok"] - at) + e["tok"]


def first(t):
    p = next((p for p in t["probes"] if p["at"] == 2000), None)
    return (ok_(p), p["right"], 2000 + p["tok"], True) if p else (ok_(t["end"]), t["end"]["right"], t["think_tok"] + t["end"]["tok"], False)


def policy(T, i, s, kind, S=()):
    s2 = s % 3 + 1; s3 = s2 % 3 + 1
    a_ok, a_r, tok, cut = first(T[s][i])
    if a_ok:
        return a_r, tok
    if kind in ("C0", "CD") and cut:
        b_ok, b_r, tok = run(T[s][i], S if kind == "CD" else (), 2000, tok)
        if b_ok:
            return b_r, tok
        c = T[s2][i]["end"]
        return c["right"], tok + T[s2][i]["think_tok"] + c["tok"]
    b_ok, b_r, t2 = run(T[s2][i], S if kind in ("RD", "CD") else ())
    if b_ok:
        return b_r, tok + t2
    c = T[s3][i]["end"]
    return c["right"], tok + t2 + T[s3][i]["think_tok"] + c["tok"]


def util(r, tok):
    return float(r) - LAM / 100 * tok / 1000


def fit(data, keys, kind):
    """greedy forward selection of cut points on the problems `keys` ((bench, id)); -> sorted tuple"""
    def score(S):
        return sum(util(*policy(data[b][0], i, s, kind, S)) for b, i in keys for s in (1, 2, 3))
    S, best = (), score(())
    while True:
        cand = [(score(tuple(sorted(S + (c,)))), c) for c in GRID if c not in S]
        if not cand or max(cand)[0] <= best:
            return S
        best, c = max(cand); S = tuple(sorted(S + (c,)))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "q8b"
    data = {b: load(tag, b) for b in BENCH}
    keys = [(b, i) for b in BENCH for i in data[b][1]]
    print(f"=== CONT {tag}: {len(keys)} problems with all three thinks ({', '.join(f'{b} {len(data[b][1])}' for b in BENCH)})")
    if not keys:
        return
    # hazard table: per cut point, how often the think is still running, the forced program passes, and is right when it passes
    print("cut   running  passes  right|passes  program tok")
    for c in GRID:
        P = [p for b, i in keys for s in (1, 2, 3) for p in data[b][0][s][i]["probes"] if p["at"] == c]
        n = 3 * len(keys)
        if P:
            okp = [p for p in P if ok_(p)]
            print(f"{c:>5} {100 * len(P) / n:7.1f}% {100 * len(okp) / len(P):6.1f}% {100 * sum(p['right'] for p in okp) / max(1, len(okp)):10.1f}% "
                  f"{sum(p['tok'] for p in P) / len(P):9.0f}")
    E = [data[b][0][s][i] for b, i in keys for s in (1, 2, 3)]
    print(f"  end   100.0% {100 * sum(ok_(t['end']) for t in E) / len(E):6.1f}% "
          f"{100 * sum(t['end']['right'] for t in E if ok_(t['end'])) / max(1, sum(ok_(t['end']) for t in E)):10.1f}%; think "
          f"{sum(t['think_tok'] for t in E) / len(E):.0f} tokens, at the cap {100 * sum(t['think_finish'] == 'length' for t in E) / len(E):.1f}%")
    folds = {f: [k for k in keys if zlib.crc32(k[1].encode()) % 2 == f] for f in (0, 1)}
    S = {kind: {f: fit(data, folds[1 - f], kind) for f in (0, 1)} for kind in ("RD", "CD")}
    for kind in S:
        print(f"{kind} cut points fitted on half 1 (scored on half 0): {S[kind][0]}; on half 0: {S[kind][1]}")
    q = {}
    for kind in ("R0", "C0", "RD", "CD", "oracle"):
        for f in (0, 1):
            for b, i in folds[f]:
                v = []
                for s in (1, 2, 3):
                    if kind == "oracle":
                        t = data[b][0][s][i]; tok = 0; at = 0; r = False
                        for p in t["probes"] + [dict(t["end"], at=t["think_tok"])]:
                            tok += max(0, p["at"] - at) + p["tok"]; at = p["at"]
                            if p["right"]:
                                r = True; break
                        v.append((r, tok))
                    else:
                        v.append(policy(data[b][0], i, s, kind, S[kind][f] if kind in S else ()))
                q.setdefault(kind, {})[f"{b}/{i}"] = (sum(r for r, _ in v) / 3, sum(util(r, t) for r, t in v) / 3, sum(t for _, t in v) / 3)
    # the stored default (other runs: formxtb2000 / formxt of the same model, analyze_hopa)
    for b in BENCH:
        A = word_rows(tag, b)
        if A:
            R = policies(A, {}, same_word)
            for i, v in per_q(R, "SB->T->T").items():
                if f"{b}/{i}" in q["R0"]:
                    q.setdefault("stored", {})[f"{b}/{i}"] = (v[0], v[1], None)
    ids = sorted(q["R0"])
    for kind, d in q.items():
        jj = [i for i in ids if i in d]
        tk = f" @ {sum(d[i][2] for i in jj) / len(jj) / 1000:.2f}k" if d[jj[0]][2] is not None else ""
        print(f"  {kind:>6}: {len(jj)} problems, accuracy {100 * sum(d[i][0] for i in jj) / len(jj):.1f}%{tk}, utility "
              f"{100 * sum(d[i][1] for i in jj) / len(jj):.2f}")
    for b in BENCH:
        jj = [i for i in ids if i.startswith(b + "/")]
        if not jj:
            continue
        print(f"  {b}: " + ", ".join(f"{k} {100 * sum(q[k][i][1] for i in jj) / len(jj):.2f}" for k in q if all(i in q[k] for i in jj)))
    # CT-P3: after a failed 2,000-token check, the end of the same think vs the end of a fresh think
    same, fresh = {}, {}
    for b, i in keys:
        for s in (1, 2, 3):
            ok, _, _, cut = first(data[b][0][s][i])
            if cut and not ok:
                same.setdefault(f"{b}/{i}", []).append(float(data[b][0][s][i]["end"]["right"]))
                fresh.setdefault(f"{b}/{i}", []).append(float(data[b][0][s % 3 + 1][i]["end"]["right"]))
    dd = {i: sum(fresh[i]) / len(fresh[i]) - sum(same[i]) / len(same[i]) for i in same} or {"none": 0.0}
    g = ci(dd)
    print(f"CT-P3 D (fresh - same end right | failed 2k check): {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] points over {len(dd)} problems "
          f"({sum(len(v) for v in same.values())} problem-seeds); continuation saves 2,000 tokens = {LAM * 2:.1f} utility points each")
    out = []
    best = "RD" if sum(q["RD"][i][1] for i in ids) >= sum(q["CD"][i][1] for i in ids) else "CD"
    for name, a, b_ in (("CT-P1 RD - R0", "RD", "R0"), ("CT-P2 C0 - R0", "C0", "R0"), ("CT-P4 CD - RD", "CD", "RD"),
                        (f"CT-P5 {best} - stored SB->T->T", best, "stored")):
        jj = [i for i in ids if i in q[a] and i in q[b_]]
        g = ci({i: q[a][i][1] - q[b_][i][1] for i in jj})
        print(f"{name}: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] ({len(jj)} problems)")
        out.append(f"{name.split()[0]} {g[1] > 0} ({g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}])")
    g = ci(dd)
    out.insert(2, f"CT-P3 {g[1] > 0} ({g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}])")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
