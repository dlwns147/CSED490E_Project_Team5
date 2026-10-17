"""H2b analysis (results/PREREG_H2B.md): single sample vs public-test-filtered best-of-k vs oracle any-of-k on the 31 contest problems.
A sample 'passes the public tests' if its first n_public tests (the statement's examples, which come first in the test order) pass.
usage: python analyze_h2b.py"""
import json

RES = "/NAS/SJ/POSTECH/nlp/results/h2"
P = {p["name"]: p for p in json.load(open(f"{RES}/cc_geometry_local.json"))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
for tag in ("q32b_plain", "oss20_low", "oss120_low"):
    S = {sd: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_{tag}_s{sd}.jsonl"))} for sd in range(1, 9)}
    names = sorted(S[1])
    for k in (1, 3, 8):
        sel = orc = tok = 0
        for n in names:
            rs = [S[sd][n] for sd in range(1, k + 1)]
            tok += sum(r.get("out_tokens") or 0 for r in rs)
            pub = [r for r in rs if r["code"] and r["passed"] >= NPUB[n]]
            pick = pub[0] if pub else rs[0]
            sel += pick["passed_all"]; orc += any(r["passed_all"] for r in rs)
        single = sum(S[sd][n]["passed_all"] for sd in range(1, k + 1) for n in names) / k
        print(f"{tag:11s} k={k}: single {100 * single / len(names):5.1f}% | public-test filtered {100 * sel / len(names):5.1f}% | oracle any-of-k "
              f"{100 * orc / len(names):5.1f}% | tokens per problem {tok / len(names):7.0f}")
