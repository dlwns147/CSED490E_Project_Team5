"""Break-even accounting of the peer cascade (offline, stored rows; 10-31): N passes its free check and the peer's quick answer is the
same -> N, else the default SB->T->T (HO-PA's form; SQL on SQL-PA's BIRD-train rows and SQL-1's dev rows). Per task x model, over
problem-seeds: n_R / n_W = passing N right / wrong; G = mean utility gain of accepting a right passing N instead of running the
default, L = mean loss of accepting a wrong one (utility = 100 x right - 0.5 x ktokens); the break-even r* = n_W L / (n_R G): an
accept rule gains on the accepted programs only if (share of right ones it accepts) / (share of wrong ones it accepts) > r* (for
accepts spread evenly over the right and over the wrong ones); then the peer's tokens on every passing N and N's own tokens are paid.
The printed "= " column is the cascade - default exactly (problem-seed weighted), split into those parts.
usage: python analyze_breakeven.py"""
import sys, contextlib, io, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_hopa as H
LAM = 0.5
def acct(name, items):
    # items: list of (n_pass, n_right, n_tok, peer_agree, peer_tok, d_right, d_tok)
    n = len(items)
    R = [x for x in items if x[0] and x[1]]; W = [x for x in items if x[0] and not x[1]]
    d = lambda x: 100 * (float(x[1]) - float(x[5])) + LAM * x[6] / 1000
    G = sum(d(x) for x in R) / max(1, len(R)); L = -sum(d(x) for x in W) / max(1, len(W))
    Ga = [d(x) for x in R if x[3]]; La = [-d(x) for x in W if x[3]]
    tpr = len(Ga) / max(1, len(R)); fpr = len(La) / max(1, len(W))
    acc_part = (sum(Ga) - sum(La)) / n
    peer_cost = LAM * sum(x[4] for x in items if x[0]) / 1000 / n
    n_cost = LAM * sum(x[2] for x in items) / 1000 / n
    rstar = len(W) * L / max(1e-9, len(R) * G)
    print(f"{name:>16}: pass {100*(len(R)+len(W))/n:4.0f}%  right|pass {100*len(R)/max(1,len(R)+len(W)):4.0f}%  G {G:5.1f}  L {L:5.1f}  "
          f"break-even TPR/FPR {rstar:4.2f}  peer TPR {100*tpr:3.0f}% FPR {100*fpr:3.0f}% ratio {tpr/max(1e-9,fpr):4.1f}  "
          f"accept gain {acc_part:+5.2f}  - peer {peer_cost:4.2f} - N {n_cost:4.2f} = {acc_part-peer_cost-n_cost:+5.2f}")
for kind in ("words", "tc"):
    H.SAME_FN = H.same_word if kind == "words" else H.same_tc
    cells = [(b, m) for m in ("q8b", "q14a", "q35") for b in H.BENCH] if kind == "words" else [(sp, m) for m in ("q8b", "q14a", "q35") for sp in ("non-live", "live")]
    load = H.word_rows if kind == "words" else H.tc_rows
    per_m = {}
    for c, m in cells:
        A, P = load(m, c), load(H.PEER[m], c)
        if A is None or P is None: continue
        R = H.policies(A, {"p": P}, H.SAME_FN)
        for (i, s), r in R.items():
            f, p = A["formx"][s][i], P["formx"][s][i]
            dd = r["SB->T->T"]
            per_m.setdefault(m, []).append((f[0], f[1], f[2], f[0] and H.SAME_FN(f, p), p[2], dd[0], dd[1]))
    for m, items in per_m.items():
        acct(f"{kind} {m}", items)
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_sqlpa as Q
for dev in (False, True):
    tag = {m: m if dev else m + "pa" for m in Q.MODELS}
    G = {m: Q.grades(tag[m]) for m in Q.MODELS}
    K = {m: Q.ntok(tag[m]) for m in Q.MODELS if G[m]}
    for A, P in Q.PEER.items():
        if not (G[A] and G[P]): continue
        B = Q.base(tag[A]); items = []
        for (i, s), v in B.items():
            n = G[A][s][i]["N"]; o = G[P][s].get(i, {}).get("N", {})
            ps = n["chk"] == "pass"
            items.append((ps, bool(n["ok"]), K[A][s][i], ps and o.get("chk") == "pass" and o.get("h") == n["h"], K[P][s].get(i, 0),
                          v["SB->T->T"][0], v["SB->T->T"][1]))
        acct(f"sql{'dev' if dev else 'tr'} {A}", items)
