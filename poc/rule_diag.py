"""PREREG_RULE2 diagnostic (not registered): why the carried rules made the quick reading worse. usage: python poc/rule_diag.py [seeds 4 5 6]
For each trrw puzzle (fresh seeds, the 250 unseen main puzzles) with an "N houses between" clue, rebuild the rule list that puzzle was shown and
translate it once more (first round, as run_zebra's trr; same seed) under four lists:
  full     the list as shown;
  noinv    the list without the inverted "between" rules (a difference of n for n houses between);
  distinct each rule text once, first occurrence kept;
  both     distinct and without inverted rules.
Prints, per variant and stream position, the "between" clues that the gold solution violates (gold used only to score). Writes results/zl_q8bh_rulediag.json."""
import ast
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
from grid_score import _norm, clue_texts, expr_eval  # noqa: E402
from run_zebra import RES, ZL_RULES, ZL_TR, zl_gold  # noqa: E402

BTW = re.compile(r"there (?:is|are) \w+ houses? between", re.I)
W = {"one": 1, "two": 2, "three": 3, "1": 1, "2": 2, "3": 3}


def inverted(u):   # a rule that maps n houses between to a distance of n
    return any(int(d) == W[m] for d, m in re.findall(r"difference of (\d+)[^.,;]*?(one|two|three|\d) houses? between", u))


def violated(c, r):   # as gp_eval.conv_main
    pos = {}
    for i, a in enumerate(r["solution"]["header"]):
        for j, y in enumerate(r["solution"]["rows"]):
            if a != "House":
                pos.setdefault(_norm(str(y[i])), set()).add(j + 1)
    try:
        e = ast.parse(c, mode="eval")
        keys = {t.slice.value for t in ast.walk(e) if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)}
        p = {k: pos.get(_norm(str(k).split(":", 1)[-1]), set()) for k in keys}
        if any(len(v) != 1 for v in p.values()):
            return None
        return not expr_eval(e, {k: next(iter(v)) for k, v in p.items()})
    except Exception:
        return None


def misreads(code, r):
    try:
        cl = [str(c) for nd in ast.parse(code or "").body if isinstance(nd, ast.Assign) and any(getattr(t, "id", "") == "clues" for t in nd.targets)
              for c in ast.literal_eval(nd.value)]
    except Exception:
        return []
    tx = clue_texts(r["puzzle"])
    return [v for c, t in zip(cl, tx) if BTW.search(t) and (v := violated(c, r)) is not None] if len(cl) == len(tx) else []


def main():
    seeds = [int(s) for s in sys.argv[1:]] or [4, 5, 6]
    P = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ["POC_DATA"], "zebralogic", "grid.jsonl")))}
    dev = [u for x in map(json.loads, open(f"{RES}/zl_q8b_trr_s1.jsonl")) for _, u in x["rules_added"]]
    jobs = []
    for s in seeds:
        mem = list(dev)
        for k, x in enumerate(map(json.loads, open(f"{RES}/zl_q8bh_trrw_s{s}.jsonl"))):
            r = P[x["id"]]
            if any(BTW.search(t) for t in clue_texts(r["puzzle"])):
                d = list(dict.fromkeys(mem))
                for v, L in [("full", mem), ("noinv", [u for u in mem if not inverted(u)]), ("distinct", d), ("both", [u for u in d if not inverted(u)])]:
                    jobs.append((s, k, x["id"], v, list(L)))
            mem += [u for _, u in x["rules_added"]]

    def one(j):
        s, k, i, v, L = j
        r, gold = P[i], zl_gold(P[i])
        msg = ZL_TR.format(p=r["puzzle"], cols=", ".join(gold), n=len(r["solution"]["rows"])) + (ZL_RULES.format(rules="\n".join(f"- {u}" for u in L)) if L else "")
        o = chat_msgs([{"role": "user", "content": msg}], think=False, max_tokens=4096, temperature=0.7, seed=s * 10007 + int(i.rsplit("-", 1)[1]))
        return {"seed": s, "pos": k, "id": i, "variant": v, "rules": len(L), "bad": misreads(last_block(o["text"], ("python", "py", "python3")), r), "tokens": o["out_tokens"]}
    with ThreadPoolExecutor(64) as ex:
        out = list(ex.map(one, jobs))
    json.dump(out, open(f"{RES}/zl_q8bh_rulediag.json", "w"))
    for v in ["full", "noinv", "distinct", "both"]:
        row = []
        for lo in range(0, 250, 50):
            b = [z for o in out if o["variant"] == v and lo <= o["pos"] < lo + 50 for z in o["bad"]]
            row.append(f"{lo}-{lo + 49}: {sum(b)}/{len(b)}")
        b = [z for o in out if o["variant"] == v for z in o["bad"]]
        print(f"{v:8s} all {sum(b)}/{len(b)} = {100 * sum(b) / max(len(b), 1):.0f}%   " + "  ".join(row), flush=True)


if __name__ == "__main__":
    main()
