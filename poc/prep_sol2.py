"""SOL-2 (docs/prereg/PREREG_ADJ.md): evidence for the adjudicating escalation. For every held-out problem-seed that the full method
escalates to thinking (not routed to a fixed solver, own program after the repair turn does not agree with the peer), write the two
disagreeing programs and their printed values. -> results/x3/adj_<m>_<set>.jsonl {id, seed, a_code, a_pred, b_code, b_pred}
(A = the model's own program after the repair turn, B = the cross-family peer's; run_nlopt.py thinkadj shows them in a seeded order).
usage: python3 poc/prep_sol2.py"""
import json
import os
import sys

sys.argv = [sys.argv[0], "--nopool"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_frontier as F  # noqa: E402

SETS = ("x3", "optmath", "optibench", "bwor", "logior")


def main():
    for m in ("q8b", "oss20"):
        for st in SETS:
            ft, fo, fk = F.files(m, st)
            O, P = F.load(fo, {st}), F.load(F.files(F.PEER[m], st)[1], {st})
            arm = "freef" if st in ("optibench", "bwor", "logior") else "mipf"
            RP = F.load(f"{F.X3}/repair_{m}_{st}_{arm}_s{{s}}.jsonl", {st})
            out = []
            for k, routed, a in F.items(m, st):
                if routed or "T>CASCR+RS" not in a:
                    continue
                o = O[k]
                vis = o.get("status") != "ok" or o["pred"] in (None, "NBS")
                r = RP.get(k) if vis else None
                q, qc = (r["pred"], r.get("code")) if r else (o["pred"], o.get("code"))
                if q is not None and q != "NBS" and F.agree(q, P[k]["pred"]):
                    continue
                out.append({"id": k[0], "seed": k[1], "a_code": qc, "a_pred": q, "b_code": P[k].get("code"), "b_pred": P[k]["pred"]})
            path = f"{F.X3}/adj_{m}_{st}.jsonl"
            with open(path, "w") as f:
                f.writelines(json.dumps(x) + "\n" for x in out)
            print(m, st, len(out), "escalated problem-seeds ->", path)


if __name__ == "__main__":
    main()
