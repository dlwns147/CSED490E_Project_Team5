"""XG (docs/prereg/PREREG_XG.md; offline on stored rows): the peer cascade with a generator from another family, gpt-oss-20b (tags
oss20 = BIRD dev, oss20pa = SQL-PA's fresh BIRD-train questions, oss20 = BFCL single-turn). N = its low-effort quick answer, the default
D = SB->T->T (SB = the medium-effort think cut at 2,000 tokens, T = the medium-effort think, the retry T at the next seed), the
cascade = N -> free check -> the peer's quick answer is the same -> N, else D (the peer's tokens paid on every passing N); peers
Qwen3.5-9B (primary) and Qwen3-8B, their stored quick rows. Items, check, "same answer" and utility (100 x right - 0.5 x ktokens) as
poc/analyze_breakeven.py / analyze_ext.py; SQL keeps the question-seeds whose N fails the check (no repair R was run for gpt-oss).
Per cell and pooled per task: accuracy / ktokens of N, D, T->T, N->T->T and the cascades; cascade - D (utility, accuracy, ktokens;
paired 95% intervals over questions, seed means), labelled dominance (accuracy up, tokens down) or a trade with its break-even
lambda; the break-even accounting (strata, peer TPR / FPR, r*).
usage: python3.11 poc/analyze_xg.py [--word]     (XG_A=<tag> XG_PEERS=<p1,p2>: another generator, the dry run;
  --word: addendum W, the word problems)"""
import contextlib, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_breakeven as BE  # noqa: E402
    import analyze_cv as CV  # noqa: E402
    import analyze_hopa as H  # noqa: E402
    import analyze_sqlpa as Q  # noqa: E402

A = os.environ.get("XG_A", "oss20")   # XG_A=q8b XG_PEERS=q35,q14a: the dry run on a stored Qwen generator
PEERS = tuple(os.environ.get("XG_PEERS", "q35,q8b").split(","))   # primary first
WORD = "--word" in sys.argv   # addendum W: the word problems (OptiBench third, BWOR, LogiOR; gpt-oss has no OptMATH think)


def sql_cell(dev, P):
    a, p = (A, P) if dev else (A + "pa", P + "pa")
    GA, GP = Q.grades(a), Q.grades(p)
    if not (GA and GP) or not all(os.path.exists(f"{CV.RES}/{a}_{x}_s{s}.jsonl") for x in ("think", "sb") for s in (1, 2, 3)):
        return None
    KA, KP, items = Q.ntok(a), Q.ntok(p), []
    for (i, s), v in CV.base(a, need_r=False).items():
        n, o = GA[s][i]["N"], GP[s].get(i, {}).get("N")
        if o is None:
            continue
        ps = n["chk"] == "pass"
        items.append(dict(id=("dev/" if dev else "tr/") + i, s=s, ps=ps, ok=bool(n["ok"]), tok=KA[s][i], ptok=KP[s].get(i, 0),
                          agree=ps and o["chk"] == "pass" and o["h"] == n["h"], dok=bool(v["SB->T->T"][0]), dtok=v["SB->T->T"][1],
                          tt=v["T->T"], ntt=v["N->T->T"]))
    return items


def tc_cell(split, P, word=False):
    """BFCL split, or (word=True, addendum W) the word-problem set `split` with H.word_rows / H.same_word"""
    load, same = (H.word_rows, H.same_word) if word else (H.tc_rows, H.same_tc)
    RA, RP = load(A, split), load(P, split)
    if not (RA and RP):
        return None
    items = []
    for (i, s), r in H.policies(RA, {"p": RP}, same).items():
        f, p = RA["formx"][s][i], RP["formx"][s][i]
        T, T2 = RA["formxt"][s][i], RA["formxt"][s % 3 + 1][i]
        tt = (T[1], T[2]) if T[0] else (T2[1], T[2] + T2[2])
        items.append(dict(id=f"{split}/{i}", s=s, ps=bool(f[0]), ok=bool(f[1]), tok=f[2], ptok=p[2], agree=bool(same(f, p)),
                          dok=bool(r["SB->T->T"][0]), dtok=r["SB->T->T"][1], tt=tt,
                          ntt=(f[1], f[2]) if f[0] else (tt[0], f[2] + tt[1])))
    return items


POL = {"N": lambda x: (x["ok"], x["tok"]), "D": lambda x: (x["dok"], x["dtok"]), "T->T": lambda x: x["tt"], "N->T->T": lambda x: x["ntt"],
       "cascade": lambda x: ((x["ok"], x["tok"] + x["ptok"]) if x["agree"] else
                             (x["dok"], x["tok"] + (x["ptok"] if x["ps"] else 0) + x["dtok"]))}


def per_q(items, f):
    """{question: seed mean of f(x)}"""
    acc = {}
    for x in items:
        acc.setdefault(x["id"], []).append(f(x))
    return {i: sum(v) / len(v) for i, v in acc.items()}


def report(name, items):
    n = len(items)
    line = "; ".join(f"{k} {100 * sum(POL[k](x)[0] for x in items) / n:.1f}% @ {sum(POL[k](x)[1] for x in items) / n / 1000:.2f}k"
                     for k in ("N", "D", "T->T", "N->T->T", "cascade"))
    print(f"  {name} ({n} question-seeds, {len({x['id'] for x in items})} questions): {line}")
    u = lambda k: (lambda x: float(POL[k](x)[0]) - H.LAM / 100 * POL[k](x)[1] / 1000)
    du = ci({i: v for i, v in per_q(items, lambda x: u("cascade")(x) - u("D")(x)).items()})
    da = ci(per_q(items, lambda x: float(POL["cascade"](x)[0]) - float(POL["D"](x)[0])))
    dt = ci(per_q(items, lambda x: (POL["cascade"](x)[1] - POL["D"](x)[1]) / 100000))   # ci() prints x100: ktokens
    lab = ("dominance" if da[0] >= 0 and dt[0] <= 0 else "worse on both" if da[0] < 0 and dt[0] >= 0 else
           f"trade, pays for lambda {'>' if da[0] < 0 else '<'} {da[0] / dt[0]:.2f} per 1k tokens")
    print(f"    cascade - D: utility {du[0]:+.2f} [{du[1]:+.2f}, {du[2]:+.2f}]; accuracy {da[0]:+.2f} [{da[1]:+.2f}, {da[2]:+.2f}]; "
          f"ktokens {dt[0]:+.2f} [{dt[1]:+.2f}, {dt[2]:+.2f}] ({lab})")
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        BE.acct(name[:16], [(x["ps"], x["ok"], x["tok"], x["agree"], x["ptok"], x["dok"], x["dtok"]) for x in items])
    print("    " + buf.getvalue().strip())
    rate = lambda f: (lambda v: (sum(x["agree"] for x in v) / max(1, len(v)), len(v)))([x for x in items if x["ps"] and f(x)])
    (arw, nrw), (awr, nwr) = rate(lambda x: x["ok"] and not x["dok"]), rate(lambda x: not x["ok"] and x["dok"])
    (tpr, _), (fpr, _) = rate(lambda x: x["ok"]), rate(lambda x: not x["ok"])
    dec, allr = arw / max(1e-9, awr), tpr / max(1e-9, fpr)
    print(f"    decisive strata: RW {nrw} (peer agrees {100 * arw:.1f}%), WR {nwr} ({100 * awr:.1f}%), ratio {dec:.2f} vs {allr:.2f} on all "
          f"passing N; SD of cascade - D per question {sd(per_q(items, lambda x: u('cascade')(x) - u('D')(x))):.1f}")
    R, W = [x for x in items if x["ps"] and x["ok"]], [x for x in items if x["ps"] and not x["ok"]]
    d = lambda x: 100 * (float(x["ok"]) - float(x["dok"])) + H.LAM * x["dtok"] / 1000
    rstar = len(W) * (-sum(map(d, W)) / max(1, len(W))) / max(1e-9, len(R) * sum(map(d, R)) / max(1, len(R)))
    return du, abs(dec / max(1e-9, allr) - 1) <= 0.3, (None if du[1] <= 0 <= du[2] else (du[1] > 0) == (allr > rstar))


def sd(d):
    v = [100 * x for x in d.values()]; m = sum(v) / len(v)
    return (sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5


def main():
    verdict = {}
    for P in PEERS:
        print(f"=== generator {A}, peer {P}")
        tasks = (("SQL", [("BIRD dev", lambda: sql_cell(True, P)), ("BIRD-train fresh", lambda: sql_cell(False, P))]),
                 ("BFCL", [("non-live", lambda: tc_cell("non-live", P)), ("live", lambda: tc_cell("live", P))]))
        if WORD:
            tasks = (("WORD", [(b, lambda b=b: tc_cell(b, P, word=True)) for b in ("optibench", "bwor", "logior")]),)
        for task, cells in tasks:
            pooled = []
            for name, f in cells:
                items = f()
                if items is None:
                    print(f"  {name}: rows missing"); continue
                report(name, items); pooled += items
            if pooled:
                verdict[(task, P)] = report(f"{task} pooled", pooled)
    print()
    if WORD:
        v = verdict.get(("WORD", PEERS[0]))
        print(f"*** XG-W1 (word problems, peer {PEERS[0]}): cascade - D lower bound > 0: " + ("rows missing" if v is None else
              f"{v[0][1] > 0} ({v[0][0]:+.2f} [{v[0][1]:+.2f}, {v[0][2]:+.2f}])"))
        print(f"*** XG-W2: the sign follows TPR / FPR vs r*: " + ("not scored (inconclusive)" if v is None or v[2] is None else str(v[2])))
        v = verdict.get(("WORD", PEERS[1]))
        if v:
            print(f"    reported: word problems, peer {PEERS[1]}: {v[0][0]:+.2f} [{v[0][1]:+.2f}, {v[0][2]:+.2f}]")
        return
    for task, k in (("SQL", "XG-P1"), ("BFCL", "XG-P2")):
        v = verdict.get((task, PEERS[0]))
        print(f"*** {k} ({task}, peer {PEERS[0]}): cascade - D lower bound > 0: " + ("rows missing" if v is None else f"{v[0][1] > 0} ({v[0][1]:+.2f})"))
    p3 = [verdict[(t, PEERS[0])][1] for t in ("SQL", "BFCL") if (t, PEERS[0]) in verdict]
    print(f"*** XG-P3: decisive-strata ratio within 30% of the all-passing ratio in {sum(p3)} / {len(p3)} pooled tasks (needs 2 / 2): {sum(p3) == 2}")
    p4 = [verdict[(t, PEERS[0])][2] for t in ("SQL", "BFCL") if (t, PEERS[0]) in verdict]
    print(f"*** XG-P4: the sign of cascade - D follows TPR / FPR vs r* in {sum(v is True for v in p4)} of {sum(v is not None for v in p4)} "
          f"scored tasks (inconclusive intervals not scored): {all(v is not False for v in p4)}")
    for task in ("SQL", "BFCL"):
        v = verdict.get((task, PEERS[1]))
        if v:
            print(f"    reported: {task}, peer {PEERS[1]}: {v[0][0]:+.2f} [{v[0][1]:+.2f}, {v[0][2]:+.2f}]")


if __name__ == "__main__":
    main()
