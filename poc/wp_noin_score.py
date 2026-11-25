"""WP-NOIN scoring (PREREG_DIFF, 2026-11-25): two thinking programs + judge on disagreements, new prompt (thinkfreen, judge _tpn) vs
WP-TP (thinkfree, judge _tp), per-problem utility paired by problem; also one program (seed mean) and the cheap plurality (oss20 freev).
usage: python wp_noin_score.py <set>"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W

st = sys.argv[1]
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def arm(mode, sfx, tag="oss120"):
    os.environ["WP_MODE"] = mode
    P, G, RN = W.pool(tag, st)
    p = f"{W.OUT}/wpplan_{tag}_{st}_judge{sfx}.jsonl"
    Z = {json.loads(l)["id"]: json.loads(l) for l in open(p)} if sfx is not None and os.path.exists(p) else {}
    right = lambda i, v: v is not None and RN.correct(v, P[i]["gold"])
    two, one, acc2, tok2 = {}, {}, {}, {}
    for i in P:
        rows = G.get(i, []); C = W.classes(rows); tp = sum(int(r.get("out_tokens") or 0) for r in rows)
        pick = C[0]["v"] if C else None; z = Z.get(i)
        if z and z.get("pick") in (1, 2) and len(C) >= 2:
            pick = C[z["pick"] - 1]["v"]
        t = tp + (z["tok"] if z else 0)
        two[i] = U(right(i, pick), t); acc2[i] = right(i, pick); tok2[i] = t
        one[i] = sum(U(right(i, W.val(r)), int(r.get("out_tokens") or 0)) for r in rows) / max(1, len(rows))
    return two, one, acc2, tok2


def ci(d):
    rng = random.Random(1); bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
    return f"{sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}]"


new2, new1, na, nt = arm("thinkfreen", "_tpn")
old2, old1, oa, ot = arm("thinkfree", "_tp")
ch, _, ca, ct = arm("freev", None, "oss20")
ids = sorted(new2)
for name, (u, a, t) in {"cheap plurality (3 x gpt-oss-20b)": (ch, ca, ct), "WP-TP two thinking + judge": (old2, oa, ot),
                        "WP-NOIN two thinking + judge": (new2, na, nt)}.items():
    print(f"{st} {name:36s} accuracy {100*sum(a[i] for i in ids)/len(ids):.1f}%  tokens {sum(t[i] for i in ids)/len(ids)/1000:.2f}k  "
          f"utility {sum(u[i] for i in ids)/len(ids):.2f}")
print(f"{st} one program (seed mean): WP-TP {sum(old1.values())/len(ids):.2f}  WP-NOIN {sum(new1.values())/len(ids):.2f}  "
      f"new - old {ci([new1[i] - old1[i] for i in ids])}")
print(f"{st} WP-NOIN two - WP-TP two: {ci([new2[i] - old2[i] for i in ids])}")
print(f"{st} WP-NOIN two - cheap plurality: {ci([new2[i] - ch[i] for i in ids])}")
print(f"{st} WP-NOIN two - WP-NOIN one: {ci([new2[i] - new1[i] for i in ids])}")
