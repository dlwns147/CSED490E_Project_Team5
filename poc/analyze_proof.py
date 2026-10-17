"""PROOF (docs/prereg/PREREG_PROOF.md): whole-proof generation on miniF2F test (Lean 4 + Mathlib), checked by the compiler.
Per model tag: statements solved with k = 1 / 2 / 4 / 8 attempts; tokens per attempt; the compile-gated loop (draw attempts in sample
order, stop at the first proof that compiles): tokens per statement and per solved statement; share of failed attempts that name an
unknown identifier (an invented lemma = a missing fact); solved by problem type.
usage: python analyze_proof.py [tag ...]   (files results/x4/lean_<tag>_test.jsonl after `run_lean.py check`)"""
import json, os, sys
from collections import Counter, defaultdict

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x4")
TYPES = ("mathd_algebra", "mathd_numbertheory", "amc12", "aime", "imo", "induction", "algebra", "numbertheory")
typ = lambda n: next((t for t in TYPES if n.startswith(t)), "other")

for tag in sys.argv[1:] or ["oss20", "q32b", "q36", "gpv2", "dspv2", "q14a_think"]:
    f = f"{RES}/lean_{tag}_test.jsonl"
    if not os.path.exists(f):
        print(tag, "missing"); continue
    R = [json.loads(l) for l in open(f)]
    if any("ok" not in r for r in R):
        print(tag, f"not checked yet ({sum('ok' in r for r in R)}/{len(R)})"); continue
    by = defaultdict(list)
    for r in R:
        by[r["name"]].append(r)
    n = len(by)
    sol = {k: sum(any(x["ok"] for x in v if x["sample"] <= k) for v in by.values()) for k in (1, 2, 4, 8)}
    seq_tok = seq_tok_solved = 0
    for v in by.values():
        v = sorted(v, key=lambda x: x["sample"]); t = 0
        for x in v:
            t += x.get("out_tokens") or 0
            if x["ok"]:
                break
        seq_tok += t; seq_tok_solved += t if any(x["ok"] for x in v) else 0
    fail = [r for r in R if not r["ok"]]
    unk = sum(bool(r.get("unknown")) for r in fail) / max(1, len(fail))
    caps = sum(r.get("finish") == "length" for r in R)
    types = Counter(typ(nm) for nm, v in by.items() if any(x["ok"] for x in v))
    print(f"{tag:10} solved@1/2/4/8 {sol[1]}/{sol[2]}/{sol[4]}/{sol[8]} of {n} | tokens/attempt {sum(r.get('out_tokens') or 0 for r in R) / len(R):.0f} "
          f"(caps {caps}) | compile-gated loop {seq_tok / n:.0f} tokens/statement vs {sum(r.get('out_tokens') or 0 for r in R) / n:.0f} for all 8 | "
          f"failed attempts naming unknown identifiers {100 * unk:.0f}% | solved by type {dict(types)}")
