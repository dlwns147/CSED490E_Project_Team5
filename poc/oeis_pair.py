"""OEIS-PAIR headroom (2026-11-25; offline, original 500 = development): which second source to buy after one gpt-oss-120b medium thinking program, for the DIFF referee?
bound = some program right; cost = first + second + referee (mean referee tokens per disagreement measured on the stored OEIS-TP rows). usage: python oeis_pair.py [oeis|oeisf]"""
import glob, json, os, sys
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x44"); pfx = sys.argv[1] if len(sys.argv) > 1 else "oeis"
def L(f):
    out = {}
    for l in open(f):
        r = json.loads(l); o = r.get("outs"); o = o if isinstance(o, list) else (eval(o) if o else [])
        out[r["id"]] = (tuple(map(str, o)), str(r["correct"]) == "True", int(r.get("out_tokens") or 0))
    return out
D = [json.loads(l) for l in open(f"{R}/{pfx}_diff_all_tp.jsonl")]
dis = [d for d in D if d["rounds"]]; rt = sum(d["oracle_tok"] for d in dis) / len(dis)
both = [d for d in dis if d["any_right"]]; acc = sum(d["right"] for d in both) / len(both)
print(f"stored OEIS-TP: referee called on {len(dis)} of {len(D)}, {rt:.0f} tokens per call-set; right on {100*acc:.1f}% of the disagreements where some program is right")
A = L(f"{R}/{pfx}_oss120M_think_s2.jsonl"); n = len(A); U = lambda a, t: 100 * a - 0.5 * t / 1000
one = sum(v[1] for v in A.values()) / n; ot = sum(v[2] for v in A.values()) / n
print(f"one thinking program (s2): {100*one:.1f}% @ {ot/1000:.2f}k, utility {U(one, ot):.2f}")
rows = []
for f in sorted(glob.glob(f"{R}/{pfx}_*_s*.jsonl")):
    b = os.path.basename(f)
    if "diff" in b or "brR" in b or b == f"{pfx}_oss120M_think_s2.jsonl" or "selb" in b:
        continue
    B = L(f)
    if len(B) < n:
        continue
    anyr = sum(A[i][1] or B[i][1] for i in A) / n; dd = [i for i in A if A[i][0] != B[i][0] and A[i][0] and B[i][0]]
    t = sum(A[i][2] + B[i][2] for i in A) / n; exp = sum(A[i][1] if A[i][0] == B[i][0] or not B[i][0] else (B[i][1] if not A[i][0] else (acc if A[i][1] or B[i][1] else 0)) for i in A) / n
    rows.append((U(exp, t + rt * len(dd) / n), b, 100 * anyr, 100 * len(dd) / n, (t + rt * len(dd) / n) / 1000, 100 * exp, sum(B[i][2] for i in A) / n / 1000))
for u, b, a, d, t, e, bt in sorted(rows, reverse=True):
    print(f"{b:38s} second costs {bt:5.2f}k  some right {a:.1f}%  disagree {d:.1f}%  expected {e:.1f}% @ {t:.2f}k  expected utility {u:.2f}")
