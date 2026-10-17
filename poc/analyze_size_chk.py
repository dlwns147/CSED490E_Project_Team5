"""SIZE-CHK (docs/prereg/PREREG_SIZE.md): cheaper-than-thinking checks for the fact program on X6, from stored rows.
FF = mipf, thinkf if mipf fails to run / print; RESAMPLE = also require equality with the next seed's mipf; CROSS-VIEW = with mip."""
import json, os, sys

X3 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
load = lambda m, a, s: {r["id"]: r for r in map(json.loads, open(f"{X3}/opt_{m}_{a}_s{s}.jsonl"))}
runs = lambda r: r["status"] == "ok" and r.get("pred") is not None
tok = lambda r: r.get("out_tokens") or 0


def same(a, b):
    try:
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


for m in sys.argv[1:] or ["q17", "q4b", "q8b", "q14a", "oss20", "q32b"]:
    res = {k: [0, 0, 0, 0, 0] for k in ("always thinkf", "FF (runs)", "RESAMPLE", "CROSS-VIEW")}   # correct, tokens, n, accepted, wrong-accepted
    for s in (1, 2, 3):
        F, F2, B, T = load(m, "mipf", s), load(m, "mipf", s % 3 + 1), load(m, "mip", s), load(m, "thinkf", s)
        for i, f in F.items():
            t = T[i]
            for k, acc, cost in (("always thinkf", None, tok(t)), ("FF (runs)", runs(f), tok(f)),
                                 ("RESAMPLE", runs(f) and runs(F2[i]) and same(f["pred"], F2[i]["pred"]), tok(f) + tok(F2[i])),
                                 ("CROSS-VIEW", runs(f) and runs(B[i]) and same(f["pred"], B[i]["pred"]), tok(f) + tok(B[i]))):
                r = res[k]; r[2] += 1
                if acc is None:
                    r[0] += t["correct"]; r[1] += cost
                elif acc:
                    r[0] += f["correct"]; r[1] += cost; r[3] += 1; r[4] += not f["correct"]
                else:
                    r[0] += t["correct"]; r[1] += cost + tok(t)
    out = []
    for k, (c, t_, n, a, w) in res.items():
        out.append(f"{k} {100 * c / n:.1f}% @ {t_ / n:.0f}" + (f" (accepts {100 * a / n:.0f}%, wrong among accepted {100 * w / max(1, a):.1f}%)" if k != "always thinkf" else ""))
    print(f"{m:5}", " | ".join(out))
