"""MT (docs/prereg/PREREG_MT.md): grade run_mt.py's rows with BFCL's own multi-turn checker (eval_runner's path: per turn, the
steps whose answer decodes to at least one call; a force-quit item fails; multi_turn_checker: the state of every involved instance
and the ground truth's execution results after each turn). Writes results/tc/mt_grades_<tag>_<arm>_s<seed>.json {id: {ok, err}}.
Runs on the login node in the grader venv:
  /home1/leesangjun/venvs/bfcl/bin/python poc/grade_mt.py <tag> [arms NTEF] [seeds 1 2 3]"""
import contextlib, io, json, os, sys

from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "tc")
DATA = os.environ.get("MT_ITEMS") or os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl", "mt_items.jsonl")


def grade(r, p, name):
    if r["force_quit"] or len(r["turns"]) != len(p["ground_truth"]):
        return {"ok": False, "err": "multi_turn:force_terminated"}
    dec = [[s["calls"] for s in t if s["calls"]] for t in r["turns"]]
    entry = {"id": p["id"], "initial_config": p["initial_config"], "involved_classes": p["involved_classes"]}
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            g = multi_turn_checker(dec, p["ground_truth"], entry, p["cat"], name)
        except Exception as e:   # an assertion inside the checker: counted as a failure, reported
            return {"ok": False, "err": f"checker:{type(e).__name__}"}
    return {"ok": bool(g["valid"]), "err": g.get("error_type")}


def main():
    tag = sys.argv[1]
    arms = sys.argv[2] if len(sys.argv) > 2 else "NTEF"
    seeds = [int(x) for x in sys.argv[3:]] or [1, 2, 3]
    P = {p["id"]: p for p in (json.loads(l) for l in open(DATA))}
    for a in arms:
        for s in seeds:
            f = f"{RES}/mt_{tag}_{a}_s{s}.jsonl"
            if not os.path.exists(f):
                continue
            R = [json.loads(l) for l in open(f)]
            G = {r["id"]: grade(r, P[r["id"]], f"g_{tag}_{a}_s{s}") for r in R}
            json.dump(G, open(f"{RES}/mt_grades_{tag}_{a}_s{s}.json", "w"))
            n = len(G)
            print(f"{tag} {a} s{s}: {n} items, right {100 * sum(g['ok'] for g in G.values()) / max(1, n):.1f}%, "
                  f"tokens {sum(r['tok'] for r in R) / max(1, n) / 1000:.2f}k, think steps {sum(r['n_think'] for r in R) / max(1, n):.2f} "
                  f"of {sum(r['n_steps'] for r in R) / max(1, n):.2f}")


if __name__ == "__main__":
    main()
