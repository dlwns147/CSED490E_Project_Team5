"""Idea 28: the model checks the solver's grid against each clue. A count-1 translation can be wrong only if the grid it gives breaks some clue as written
(the puzzle has one solution), and reading one clue against a filled table needs no search. So a flag on any clue sends the puzzle on down the ladder.
Closest prior work: Semantic Self-Verification (Raza and Milic-Frayling, IJCAI 2025, 2501.16961) checks the formalization with model-written examples per
constraint; here the example is the solver's own answer and the model is the checker.

Usage (on a GPU lane):  $P poc/gp_check.py run <tag> <set gridpuzzle|lgp> <arm check|checkt> [--dev]
  re-runs each count-1 program in results/{gp,lgp}_<tag>[_dev]_{gtr,gtrt}_s*.jsonl under GP_SOLVE, asks for a per-clue check of the grid it prints,
  and writes results/{gp,lgp}_<tag>[_dev]_<arm>.jsonl (one row per program).
Offline:  python poc/gp_check.py eval <tag> <think tag> [--dev]   ladder with and without the check, seed 1, as idea 28's decision rule reads it.
--per-clue: one call per clue (idea 31); --nothink: enumt's checks without thinking.
--label L writes <L> in place of the arm in the output name (idea 30: the same check from another model family).
--salt N: another sample of the same check, seeds shifted by N (idea 32: repeated whole-grid checks at the per-clue cost).
Idea 29, arm enumt: for each program whose final count is 2, the solver lists up to 16 solutions and each grid gets the thinking check; if exactly one grid
passes, the step is settled with it. Read by `eval` (with the checkt rows) at K = the next step's mean dev ktok over the mean check ktok.
"""
import glob
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
CHECK = ("{p}\n\nHere is a filled table for this puzzle, one row per {first}:\n{table}\n\nDo not solve the puzzle. Check the table against each clue in turn: "
         "for each clue write its number, yes if the table satisfies the clue as written or no if it does not, and a short reason. "
         "On the last line give JSON {{\"violated\": [the numbers of the clues the table breaks]}}.")

CHECK_PC = ("{head}\n\nHere is a filled table for this puzzle, one row per {first}:\n{table}\n\nClue {num}: {clue}\n\nDoes the table satisfy this clue exactly as written? "
            "Check it carefully, then end with a line \"Answer: yes\" or \"Answer: no\".")


def run_main():
    from concurrent.futures import ThreadPoolExecutor
    from llm import chat_msgs
    from sandbox import run_python
    from run_zebra import GP_SOLVE, gp_score
    tag, src, arm = sys.argv[2], sys.argv[3], sys.argv[4]
    dev = "--dev" in sys.argv
    pre = "gp" if src == "gridpuzzle" else src
    P = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ["POC_DATA"], src, "grid.jsonl")))}
    todo = []
    for f in sorted(glob.glob(f"{RES}/{pre}_{tag}{'_dev' if dev else ''}_gtr*_s*.jsonl")):
        m = re.search(r"_(gtrt?)_s(\d+)\.jsonl$", f)
        if not m:   # e.g. *.crashed_tgrest.jsonl, partial files kept for the record
            continue
        tr, sd = m.groups()
        todo += [(tr, int(sd), x) for x in map(json.loads, open(f)) if x["count"] == (2 if arm == "enumt" else 1)]

    def run(a):
        tr, sd, x = a
        r = P[x["id"]]
        (first, fv), cols = r["cats"][0], [c for c, _ in r["cats"][1:]]
        solve = GP_SOLVE.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first))
        if arm == "enumt":
            return enum(x, r, tr, sd, first, fv, cols, solve)
        res = run_python(x["code"] + "\n" + solve, "", timeout=30, mem_bytes=4 << 30)
        try:
            out = json.loads(res.stdout.strip().splitlines()[-1])
        except (AttributeError, IndexError, ValueError):
            out = {"count": -1, "grid": {}}
        row = {"id": x["id"], "size": x["size"], "tr": tr, "seed": sd, "exact_saved": x["exact"], "count": out["count"]}
        if out["count"] != 1:   # the saved row was count 1; a different count now means the interface moved since the run
            return {**row, "exact": False, "violated": None, "tokens": 0}
        g = out["grid"]
        ex, _ = gp_score(g, r)
        vio, o = check(r, first, fv, cols, g, arm == "checkt", sd * 10007 + int(x["id"].split("-")[1]) + 99)
        return {**row, "exact": ex, "violated": vio, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-2500:]}

    def check(r, first, fv, cols, g, think, seed):
        if "--salt" in sys.argv:   # idea 32: another sample of the same check (salt 0 = the original seeds)
            seed += 1000003 * int(sys.argv[sys.argv.index("--salt") + 1])
        table = "\n".join(f"{v} | " + " | ".join(f"{c}: {g.get(c, [None] * len(fv))[k]}" for c in cols) for k, v in enumerate(fv))
        if "--per-clue" in sys.argv:
            return check_pc(r, first, table, think, seed)
        o = chat_msgs([{"role": "user", "content": CHECK.format(p=r["puzzle"], first=first, table=table)}], think=think,
                      max_tokens=8000 if think else 2048, temperature=0.7, seed=seed)
        m = re.findall(r"\{[^{}]*\"violated\"[^{}]*\}", o["text"] or "")
        try:
            vio = [int(k) for k in json.loads(m[-1])["violated"]]
        except (IndexError, ValueError, TypeError, KeyError):
            vio = None   # unparsed: read as no flag
        return vio, o

    def check_pc(r, first, table, think, seed):
        # idea 31: one call per clue, each seeing only the setup, the table and that clue (the factored checks of Chain-of-Verification, 2309.11495)
        t = r["puzzle"]
        head, body = t[:t.find("Clues:")], t[t.find("Clues:") + 6:t.find("While answering") if "While answering" in t else None]
        clues = re.findall(r"^\s*(\d+)\.\s*(.+)$", body, re.M)
        def one(a):
            k, (num, c) = a
            o = chat_msgs([{"role": "user", "content": CHECK_PC.format(head=head.strip(), first=first, table=table, num=num, clue=c.strip())}], think=think,
                          max_tokens=4000 if think else 1024, temperature=0.7, seed=seed + 1000 * (k + 1))
            v = re.findall(r"Answer:\W*(yes|no)\b", o["text"] or "", re.I)
            return int(num), (v[-1].lower() if v else None), o
        res = list(map(one, enumerate(clues)))
        vio = [n for n, v, _ in res if v == "no"]
        return vio, {"out_tokens": sum(o["out_tokens"] for _, _, o in res), "finish": ",".join(sorted({o["finish"] for _, _, o in res})),
                     "text": " | ".join(f"{n}:{v}" for n, v, _ in res)}

    def enum(x, r, tr, sd, first, fv, cols, solve):
        # list up to 16 solutions (17 found means more than 16), then check each grid
        solve = solve.replace("if len(self.s) >= 2:", "if len(self.s) >= 17:").replace('print(json.dumps({"count": len(cb.s), "grid": g}))', "")
        solve += "\ngs = [{a: [x for _, x in sorted((t[f'{a}:{x}'], x) for x in vals)] for a, vals in groups.items()} for t in cb.s]\nprint(json.dumps({'count': len(cb.s), 'grids': gs}))\n"
        res = run_python(x["code"] + "\n" + solve, "", timeout=60, mem_bytes=4 << 30)
        try:
            out = json.loads(res.stdout.strip().splitlines()[-1])
        except (AttributeError, IndexError, ValueError):
            out = {"count": -1, "grids": []}
        row = {"id": x["id"], "size": x["size"], "tr": tr, "seed": sd, "count": out["count"], "grids": []}
        if not 2 <= out["count"] <= 16:
            return {**row, "exact": False, "pick": None, "tokens": 0}
        for k, g in enumerate(out["grids"]):
            vio, o = check(r, first, fv, cols, g, "--nothink" not in sys.argv, sd * 10007 + int(x["id"].split("-")[1]) + 199 + k)
            row["grids"].append({"exact": gp_score(g, r)[0], "violated": vio, "tokens": o["out_tokens"]})
        ok = [k for k, z in enumerate(row["grids"]) if not z["violated"]]
        return {**row, "pick": ok[0] if len(ok) == 1 else None, "exact": len(ok) == 1 and row["grids"][ok[0]]["exact"],
                "gold_in": any(z["exact"] for z in row["grids"]), "tokens": sum(z["tokens"] for z in row["grids"])}

    lab = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else arm   # e.g. checkt_oss: the same arm with another model serving
    path = f"{RES}/{pre}_{tag}{'_dev' if dev else ''}_{lab}.jsonl"
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, todo):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    if arm == "enumt":
        print(tag, src, arm, f"programs {len(rows)}, listed 2-16 {sum(2 <= r['count'] <= 16 for r in rows)}, gold among them {sum(r.get('gold_in', False) for r in rows)}, "
              f"one grid passes {sum(r['pick'] is not None for r in rows)}, of which right {sum(r['exact'] for r in rows)}", flush=True)
        return
    wr = [r for r in rows if not r["exact"]]
    print(tag, src, arm, f"programs {len(rows)}, wrong {len(wr)}, flagged wrong {sum(bool(r['violated']) for r in wr)}, "
          f"flagged right {sum(bool(r['violated']) for r in rows if r['exact'])}, saved/replayed exact differ {sum(r['exact'] != r['exact_saved'] for r in rows)}", flush=True)


def eval_main():
    """Decision rule fixed in IDEAS row 28 before the run: per set, seed 1, ladder gtr -> gtrt -> think, with the check a count-1 step whose grid gets a
    flag goes on to the next step (check tokens paid on every count-1 step). Utility 100*right - 0.5*ktok, bootstrap over puzzles."""
    tag, ttag = sys.argv[2], sys.argv[3]
    d = "_dev" if "--dev" in sys.argv else ""
    for pre in ["gp", "lgp"]:
        for arm in ["check", "checkt"]:
            cp = f"{RES}/{pre}_{tag}{d}_{arm}.jsonl"
            if not os.path.exists(cp):
                continue
            C = {(r["tr"], r["id"], r["seed"]): r for r in map(json.loads, open(cp))}
            allc = list(C.values())
            for tr in ["gtr", "gtrt"]:
                rs = [r for r in allc if r["tr"] == tr]
                if rs:
                    a = [r for r in rs if not r["violated"]]
                    print(f"{pre} {arm} {tr}: count-1 programs {len(rs)} (right {sum(r['exact'] for r in rs)}), unflagged {len(a)} (right {sum(r['exact'] for r in a)}); "
                          f"wrong flagged {sum(bool(r['violated']) for r in rs if not r['exact'])}/{sum(not r['exact'] for r in rs)}, "
                          f"right flagged {sum(bool(r['violated']) for r in rs if r['exact'])}/{sum(r['exact'] for r in rs)}, unparsed {sum(r['violated'] is None for r in rs)}, "
                          f"check ktok {sum(r['tokens'] for r in rs) / len(rs) / 1000:.2f}")
            L = {t: {x["id"]: x for x in map(json.loads, open(f"{RES}/{pre}_{tag}{d}_{t}_s1.jsonl"))} for t in ["gtr", "gtrt"]}
            T = {x["id"]: x for x in map(json.loads, open(f"{RES}/{pre}_{ttag}{d}_think_s1.jsonl"))}
            ids = sorted(set(L["gtr"]) & set(L["gtrt"]) & set(T))
            du = {}
            uu = {"plain": [], "check": []}
            for i in ids:
                u = {}
                for use in [False, True]:
                    tok, right = 0, None
                    for t in ["gtr", "gtrt"]:
                        x = L[t][i]
                        tok += x["tokens"]
                        if x["count"] == 1:
                            c = C.get((t, i, 1))
                            if use and c is not None:
                                tok += c["tokens"]
                            if not (use and c is not None and c["violated"]):
                                right = x["exact"]
                                break
                    if right is None:
                        tok += T[i]["tokens"]
                        right = T[i]["exact"]
                    u[use] = 100 * right - 0.5 * tok / 1000
                uu["plain"].append(u[False]); uu["check"].append(u[True])
                du[i] = u[True] - u[False]
            rng = random.Random(0)
            k = sorted(du)
            bs = sorted(sum(du[rng.choice(k)] for _ in k) / len(k) for _ in range(10000))
            pt = sum(du.values()) / len(k)
            print(f"{pre} {arm} ladder seed 1, {len(k)} puzzles: utility plain {sum(uu['plain']) / len(k):.1f}, with check {sum(uu['check']) / len(k):.1f}, "
                  f"difference {pt:+.1f} [{bs[250]:+.1f}, {bs[9749]:+.1f}] -> {'survives' if pt > 0 else 'killed'} on this set")
            ep = f"{RES}/{pre}_{tag}{d}_enumt.jsonl"
            if arm == "checkt" and os.path.exists(ep):
                eval_enum(pre, tag, d, ttag, C, L, T, ids, ep)


def eval_enum(pre, tag, d, ttag, C, L, T, ids, ep):
    """Idea 29, rule fixed in IDEAS row 29 before the run: seed 1, the checked ladder plus, at a count-2 step, the listed grids (if at most K) each checked;
    exactly one passing grid settles the step. K per step = the next step's mean dev ktok over the mean dev check ktok (dev values, all seeds)."""
    E = {(r["tr"], r["id"], r["seed"]): r for r in map(json.loads, open(ep))}
    mk = lambda f: sum(x["tokens"] for x in map(json.loads, open(f))) / sum(1 for _ in open(f)) / 1000
    ck = sum(r["tokens"] for r in C.values()) / len(C) / 1000
    nxt = {"gtr": sum(mk(f) for f in glob.glob(f"{RES}/{pre}_{tag}_dev_gtrt_s*.jsonl")) / len(glob.glob(f"{RES}/{pre}_{tag}_dev_gtrt_s*.jsonl")),
           "gtrt": mk(f"{RES}/{pre}_{ttag}_dev_think_s1.jsonl")}
    K = {t: min(16, int(nxt[t] / ck)) for t in nxt}   # 17 means more than 16 were found, none listed
    rs = [r for r in E.values() if 2 <= r["count"] <= K[r["tr"]]]
    print(f"{pre} enumt: K {K} (check {ck:.2f} ktok); count-2 programs {len(E)}, listed within K {len(rs)}, right grid among them {sum(r['gold_in'] for r in rs)}, "
          f"one grid passes {sum(r['pick'] is not None for r in rs)}, of which right {sum(r['exact'] for r in rs)}, mean check ktok {sum(r['tokens'] for r in rs) / max(len(rs), 1) / 1000:.1f}")
    du = {}
    for i in ids:
        u = []
        for use in [False, True]:
            tok, right = 0, None
            for t in ["gtr", "gtrt"]:
                x = L[t][i]
                tok += x["tokens"]
                if x["count"] == 1:
                    c = C[(t, i, 1)]
                    tok += c["tokens"]
                    if not c["violated"]:
                        right = x["exact"]
                        break
                e = E.get((t, i, 1))
                if use and x["count"] == 2 and e and 2 <= e["count"] <= K[t]:
                    tok += e["tokens"]
                    if e["pick"] is not None:
                        right = e["exact"]
                        break
            if right is None:
                tok += T[i]["tokens"]
                right = T[i]["exact"]
            u.append(100 * right - 0.5 * tok / 1000)
        du[i] = u[1] - u[0]
    rng = random.Random(0)
    k = sorted(du)
    bs = sorted(sum(du[rng.choice(k)] for _ in k) / len(k) for _ in range(10000))
    pt = sum(du.values()) / len(k)
    print(f"{pre} enumt ladder seed 1, {len(k)} puzzles: checked ladder with listing minus checked ladder {pt:+.1f} [{bs[250]:+.1f}, {bs[9749]:+.1f}] -> "
          f"{'survives' if pt > 0 else 'killed'} on this set")


if __name__ == "__main__":
    {"run": run_main, "eval": eval_main}[sys.argv[1]]()
