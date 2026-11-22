"""SOL-2 first test (LOOP §2, 2026-11-22; exploratory upper bound, decides only whether SOL-2 gets registered): on held-out problems
that the full method (PREREG_ESCT) escalates and still gets wrong while thinking printed a value (not a visible failure), how often is
one of the two disagreeing programs — the model's own (after the repair turn) or the cross-family peer's — right? A thinker that
adjudicates between them can at most recover these. Rule fixed before running: < 25% of such rows → SOL-2 dropped.
usage: [OR_CLEAN=1] python3 poc/analyze_sol2.py"""
import os
import sys

sys.argv = [sys.argv[0], "--nopool"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_frontier as F  # noqa: E402

SETS = ("x3", "optmath", "optibench", "bwor", "logior")
FINAL = {"q8b": "T>CASCR+RX", "oss20": "T>CASCR+RS"}


def main():
    print(f"labels: {'expert-audited' if F.CLEAN else 'raw'}")
    for m in ("q8b", "oss20"):
        c = dict(rows=0, esc=0, wrong=0, vis=0, val=0, own=0, peer=0, either=0, both_none=0)
        for st in SETS:
            ft, fo, fk = F.files(m, st)
            O, P, K = F.load(fo, {st}), F.load(F.files(F.PEER[m], st)[1], {st}), F.load(fk, {st}) if fk else {}
            arm = "freef" if st in ("optibench", "bwor", "logior") else "mipf"
            RP = F.load(f"{F.X3}/repair_{m}_{st}_{arm}_s{{s}}.jsonl", {st})
            for k, routed, a in F.items(m, st):
                if FINAL[m] not in a or routed:
                    continue
                c["rows"] += 1
                o, g = O[k], F.gold_of(k[0], O[k]["gold"])
                vis = o.get("status") != "ok" or o["pred"] in (None, "NBS")
                r = RP.get(k) if vis else None
                q = r["pred"] if r else o["pred"]
                if q is not None and q != "NBS" and F.agree(q, P[k]["pred"]):
                    continue                                    # accepted by agreement: not escalated
                c["esc"] += 1
                if a[FINAL[m]][0]:
                    continue
                c["wrong"] += 1
                if K[k].get("status") != "ok" or K[k]["pred"] in (None, "NBS"):
                    c["vis"] += 1; continue                     # visible think failure: the retry's case, not SOL-2's
                c["val"] += 1
                ow = q not in (None, "NBS") and F.correct(q, g); pw = P[k]["pred"] not in (None, "NBS") and F.correct(P[k]["pred"], g)
                c["own"] += ow; c["peer"] += pw; c["either"] += ow or pw
                c["both_none"] += q in (None, "NBS") and P[k]["pred"] in (None, "NBS")
        v = max(1, c["val"])
        print(f"  {m}: {c['rows']} non-routed rows, escalated {c['esc']}, final wrong {c['wrong']} (visible think failure {c['vis']},"
              f" think printed a wrong value {c['val']}); among the latter own right {c['own']} ({100 * c['own'] / v:.0f}%), peer right"
              f" {c['peer']} ({100 * c['peer'] / v:.0f}%), either {c['either']} ({100 * c['either'] / v:.0f}%); both printed nothing {c['both_none']}")


if __name__ == "__main__":
    main()
