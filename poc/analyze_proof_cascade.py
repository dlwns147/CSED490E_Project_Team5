"""PROOF-C (docs/prereg/PREREG_PROOF.md): cheap general model first (up to k1 attempts), specialized prover only when none compiles.
Cost = output tokens and compute = active parameters (B) x output tokens. Uses stored, checked attempts 1-8 only."""
import json, os, sys

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x4")
ACTIVE = {"q36": 3.0, "oss20": 3.6, "gpv2": 8.2, "dspv2": 6.9, "q32b": 32.8}


def attempts(tag):
    by = {}
    for l in open(f"{RES}/lean_{tag}_test.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if "ok" in r and r["sample"] <= 8:
            by.setdefault(r["name"], []).append(r)
    return {n: sorted(v, key=lambda x: x["sample"]) for n, v in by.items()}


def gated(rows, k):
    t = 0
    for x in rows[:k]:
        t += x.get("out_tokens") or 0
        if x["ok"]:
            return True, t
    return False, t


def run(first, k1, second, k2=8):
    A, B = attempts(first), attempts(second)
    names = sorted(set(A) & set(B))
    ok = tok = comp = 0
    for n in names:
        s1, t1 = gated(A[n], k1); tok += t1; comp += ACTIVE[first] * t1
        if s1:
            ok += 1; continue
        s2, t2 = gated(B[n], k2); tok += t2; comp += ACTIVE[second] * t2; ok += s2
    return ok, tok / len(names), comp / len(names), len(names)


if __name__ == "__main__":
    for second in ("gpv2", "dspv2"):
        ok, tok, comp, n = run(second, 0, second)
        print(f"{second} alone (8 attempts, compile-gated): {ok}/{n} @ {tok / 1000:.1f}k tokens, compute {comp / 1000:.0f}k")
        for first in ("q36", "oss20"):
            for k1 in (1, 2, 4):
                ok2, tok2, comp2, _ = run(first, k1, second)
                print(f"  {first} x{k1} -> {second}: {ok2}/{n} @ {tok2 / 1000:.1f}k tokens ({100 * tok2 / tok:.0f}%), compute {comp2 / 1000:.0f}k ({100 * comp2 / comp:.0f}%)")
