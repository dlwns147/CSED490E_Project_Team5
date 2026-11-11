"""Rescore grid runs with poc/grid_score.py (scoring v2). Thinking rows: the answer is re-read from the stored text. Program rows (gtr, gtrt and their
one-round samples): the stored program is re-run under GP_SOLVE in the sandbox (model-written code: run this in the container), or the stored grid is
used when the row has one. Writes results/{gp,lgp}_<tag>_score2.json, {"<arm>|<id>|<seed>": [exact, count]}; poc/gp_eval.py --score2 reads it.
usage: $P poc/gp_rescore.py <tag> [...]
       $P poc/gp_rescore.py --zl <tag> [...]   ZebraLogic: thinking rows from their text, program rows from their stored grid or, for rows written
       before grids were kept, by re-running the final program under ZL_SOLVE (container); the listed values of an attribute are its gold values;
       writes results/zl_<tag>_score2.json for poc/gp_eval.py --zl <tag> --score2."""
import glob
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from grid_score import score  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")


def main():
    from run_zebra import GP_SOLVE, zl_extract
    from sandbox import run_python
    for tag in sys.argv[1:]:
        for s, src in [("gp", "gridpuzzle"), ("lgp", "lgp")]:
            P = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ["POC_DATA"], src, "grid.jsonl")))}
            todo = []
            for f in sorted(glob.glob(f"{RES}/{s}_{tag}_*_s*.jsonl")):
                m = re.search(rf"{s}_{re.escape(tag)}_(gtr|gtrt|think|direct)_s(\d+)\.jsonl$", f)
                if m:
                    todo += [(m.group(1), int(m.group(2)), x) for x in map(json.loads, open(f))]

            def one(a):
                arm, sd, x = a
                r = P[x["id"]]
                if arm in ("think", "direct"):
                    g = x["grid"] if "grid" in x else zl_extract(x.get("text") or "")
                    return f"{arm}|{x['id']}|{sd}", [score(g, r)[0], None]
                if "grid" in x or not x.get("code"):   # program rows also keep their solution grid (third field; PREREG_FREE's OR check reads it)
                    return f"{arm}|{x['id']}|{sd}", [score(x.get("grid"), r)[0], x["count"], x.get("grid")]
                fv, first = r["cats"][0][1], r["cats"][0][0]
                res = run_python(x["code"] + "\n" + GP_SOLVE.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first)), "",
                                 timeout=30, mem_bytes=4 << 30)
                try:
                    out = json.loads(res.stdout.strip().splitlines()[-1])
                except (AttributeError, IndexError, ValueError):
                    out = {"count": -1, "grid": {}}
                return f"{arm}|{x['id']}|{sd}", [score(out["grid"], r)[0], out["count"], out["grid"]]
            with ThreadPoolExecutor(16) as ex:
                D = dict(ex.map(one, todo))
            json.dump(D, open(f"{RES}/{s}_{tag}_score2.json", "w"))
            ch = sum(1 for (arm, sd, x) in todo if D[f"{arm}|{x['id']}|{sd}"][0] != x["exact"])
            moved = sum(1 for (arm, sd, x) in todo if arm in ("gtr", "gtrt") and "grid" not in x and D[f"{arm}|{x['id']}|{sd}"][1] != x["count"])
            print(tag, s, f"{len(todo)} rows, {ch} change exact, {moved} programs whose count differs on re-run", flush=True)


def zl_main():
    from run_zebra import ZL_SOLVE, zl_extract
    from sandbox import run_python

    moved = []

    def grid(x):
        if "grid" in x:
            return x["grid"]
        if "hist" not in x:
            return zl_extract(x.get("text") or "")
        if not x.get("code"):
            return {}
        res = run_python(x["code"] + "\n" + ZL_SOLVE, "", timeout=30, mem_bytes=4 << 30)
        try:
            out = json.loads(res.stdout.strip().splitlines()[-1])
        except (AttributeError, IndexError, ValueError):
            out = {"count": -1, "grid": {}}
        if out.get("count") != x["count"]:
            moved.append(x["id"])
        return out.get("grid", {})

    P = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ.get("POC_DATA", os.path.join(RES, "..", "..", "nlp_data")), "zebralogic", "grid.jsonl")))}
    for tag in [a for a in sys.argv[1:] if a != "--zl"]:
        D, ch = {}, 0
        for f in sorted(glob.glob(f"{RES}/zl_{tag}_*_s*.jsonl")):
            m = re.search(rf"zl_{re.escape(tag)}_([a-z]+)_s(\d+)\.jsonl$", f)
            if not m:
                continue
            X = list(map(json.loads, open(f)))
            with ThreadPoolExecutor(16) as ex:
                G = list(ex.map(grid, X))
            for x, g in zip(X, G):
                r = P[x["id"]]
                h, rows = r["solution"]["header"], r["solution"]["rows"]
                gold = {a: [str(y[i]).strip() for y in rows] for i, a in enumerate(h) if a != "House"}
                e = score(g, {"cats": [("House", [])] + [(a, v) for a, v in gold.items()], "gold": gold})[0]
                D[f"{m.group(1)}|{x['id']}|{m.group(2)}"] = [e, x.get("count")]
                ch += e != x["exact"]
        json.dump(D, open(f"{RES}/zl_{tag}_score2.json", "w"))
        print(tag, f"{len(D)} rows, {ch} change exact, {len(moved)} programs whose count differs on re-run", flush=True)
        moved.clear()


def zl_min():
    """PREREG_FREE addendum FREE-MIN: is every clue of a count-1 ZebraLogic program needed? ZebraLogic's generator removes clues until none can go
    (Lin et al. 2502.01100), so in a faithful translation dropping any one clue leaves more than one solution. Each stored count-1 program (arms tr,
    trt, trf) is re-run once per clue with that clue dropped (container: model-written code). -> results/zl_<tag>_min.json
    {"<arm>|<id>|<seed>": [count with all clues, [count without clue j for each j]]}"""
    from run_zebra import ZL_SOLVE
    from sandbox import run_python

    def count(code):
        res = run_python(code + "\n" + ZL_SOLVE, "", timeout=30, mem_bytes=4 << 30)
        try:
            return json.loads(res.stdout.strip().splitlines()[-1])["count"]
        except (AttributeError, IndexError, ValueError, KeyError):
            return -1
    for tag in [a for a in sys.argv[1:] if not a.startswith("--")]:
        todo = []
        for f in sorted(glob.glob(f"{RES}/zl_{tag}_*_s*.jsonl")):
            m = re.search(rf"zl_{re.escape(tag)}_(tr|trt|trf)_s(\d+)\.jsonl$", f)
            if m:
                todo += [(m.group(1), int(m.group(2)), x) for x in map(json.loads, open(f)) if x.get("count") == 1 and x.get("code")]

        def one(a):
            import ast
            arm, sd, x = a
            try:   # the number of clue expressions, read from the program's syntax (not run)
                nc = next(len(n.value.elts) for n in ast.parse(x["code"]).body if isinstance(n, ast.Assign) and isinstance(n.value, ast.List)
                          and any(isinstance(t, ast.Name) and t.id == "clues" for t in n.targets))
            except (StopIteration, SyntaxError, ValueError):
                return f"{arm}|{x['id']}|{sd}", [count(x["code"]), None]
            drops = [count(x["code"] + f"\nclues = list(clues)[:{k}] + list(clues)[{k} + 1:]\n") for k in range(nc)]
            return f"{arm}|{x['id']}|{sd}", [count(x["code"]), drops]
        with ThreadPoolExecutor(int(os.environ.get("ZLMIN_WORKERS", 16))) as ex:
            D = dict(ex.map(one, todo))
        json.dump(D, open(f"{RES}/zl_{tag}_min.json", "w"))
        print(tag, len(D), "programs", flush=True)


if __name__ == "__main__":
    zl_min() if "--zlmin" in sys.argv else zl_main() if "--zl" in sys.argv else main()
