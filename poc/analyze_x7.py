"""X7 (docs/prereg/PREREG_X7.md): MAMO held-out. Policies with the hand-written fact (mipf x2, thinkf) and the automatic fact (mips x2,
thinks): CHEAP, FF (think if the program does not run), FFR (think unless two programs run and agree), THINK; pilot-of-30 policy choice."""
import json, os, random, sys

X3 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
runs = lambda r: r["status"] == "ok" and r.get("pred") is not None


def same(a, b):
    try:
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


def rows(tag, a, s):
    f = f"{X3}/opt_{tag}_{a}_s{s}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def items(tag, c, t):
    C1, C2, T = rows(tag, c, 1), rows(tag, c, 2), rows(tag, t, 1)
    if not (C1 and C2 and T):
        return None
    out = []
    for i, r in C1.items():
        if i in C2 and i in T:
            r2, tr = C2[i], T[i]
            out.append(dict(src=r["src"], f_ok=r["correct"], f_pass=runs(r), f_tok=r["out_tokens"] or 0, f2_tok=r2["out_tokens"] or 0,
                            agree=runs(r) and runs(r2) and same(r["pred"], r2["pred"]), t_ok=tr["correct"], t_tok=tr["out_tokens"] or 0))
    return out


def pol(it):
    n = len(it); acc = dict(CHEAP=0, FF=0, FFR=0, THINK=0); tok = dict.fromkeys(acc, 0)
    for x in it:
        acc["CHEAP"] += x["f_ok"]; tok["CHEAP"] += x["f_tok"]; acc["THINK"] += x["t_ok"]; tok["THINK"] += x["t_tok"]
        acc["FF"] += x["f_ok"] if x["f_pass"] else x["t_ok"]; tok["FF"] += x["f_tok"] + (0 if x["f_pass"] else x["t_tok"])
        acc["FFR"] += x["f_ok"] if x["agree"] else x["t_ok"]; tok["FFR"] += x["f_tok"] + x["f2_tok"] + (0 if x["agree"] else x["t_tok"])
    return {p: (100 * acc[p] / n, tok[p] / n / 1000) for p in acc}


for m in sys.argv[1:] or ["q32b", "q14a", "oss20", "q8b"]:
    tag = f"{m}_mamo"; nofact = rows(tag, "mip", 1)
    print(f"=== {m} on MAMO" + (f" (no fact: {100 * sum(r['correct'] for r in nofact.values()) / len(nofact):.1f}%)" if nofact else ""))
    for name, (c, t) in (("hand-written", ("mipf", "thinkf")), ("automatic", ("mips", "thinks"))):
        it = items(tag, c, t)
        if not it:
            print(f"  {name}: incomplete"); continue
        P = pol(it)
        print(f"  {name:12} " + " | ".join(f"{p} {a:.1f}%@{k:.1f}k" for p, (a, k) in P.items())
              + "  [easy / complex FFR: " + " / ".join(f"{pol([x for x in it if x['src'] == s])['FFR'][0]:.1f}" for s in ("mamo_easy", "mamo_complex")) + "]")
        if name == "automatic":
            u = lambda P: {p: a - 0.5 * k for p, (a, k) in P.items()}
            full = u(P); best = max(full, key=full.get); rng = random.Random(0); reg = []
            for _ in range(1000):
                pick = max((v := u(pol(rng.sample(it, 30)))), key=v.get); reg.append(full[best] - full[pick])
            print(f"  automatic: best policy {best}; pilot-of-30 regret {sum(reg) / len(reg):.2f} points (lambda 0.5)")
