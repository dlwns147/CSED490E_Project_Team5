"""SQL-1 (docs/prereg/PREREG_SQL.md): the free check and BIRD's execution accuracy for run_sql.py's rows. Per question, seed and arm (N, R,
T, SB): the extracted query runs read-only on the question's database (30 s); chk = 'pass' (no error, at least one row) or what the
check saw; ok = its set of result rows equals the gold query's; h = a hash of that set (agreement between two queries). Questions whose
gold query fails or times out are listed under "_gold_fail" and left out of the analysis.
usage: python grade_sql.py <tag> [seeds]   -> results/sql/grades_<tag>_s<seed>.json (resumes)"""
import hashlib, json, os, sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prep_sql import DATA, execute, extract  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
_GOLD = {}


def rowset(rows):
    return frozenset(rows)


def digest(rows):
    return hashlib.md5(repr(sorted(map(repr, set(rows)))).encode()).hexdigest()[:16]


def grade(key, db, gold, sql):
    if gold not in _GOLD:
        rows, err = execute(db, extract(gold))
        _GOLD[gold] = None if err else rowset(rows)
    g = _GOLD[gold]
    if g is None:
        return key, None
    rows, err = execute(db, sql)
    return key, {"ok": err is None and rowset(rows) == g, "chk": "pass" if err is None and rows else (err or "no rows"),
                 "h": digest(rows) if err is None else None}


def main():
    tag, seeds = sys.argv[1], [int(s) for s in (sys.argv[2:] or ["1", "2", "3"])]
    I = {r["id"]: r for r in map(json.loads, open(f"{DATA}/sql_items.jsonl"))}
    workers = int(os.environ.get("SQL_WORKERS", len(os.sched_getaffinity(0))))
    for s in seeds:
        gp = f"{RES}/grades_{tag}_s{s}.json"
        G = json.load(open(gp)) if os.path.exists(gp) else {}
        C = {r["id"]: r for r in _rows(f"{RES}/{tag}_cheap_s{s}.jsonl")}
        texts = {"N": {i: r.get("n_text") for i, r in C.items()}, "R": {i: r["r_text"] for i, r in C.items() if "r_text" in r},
                 "T": {r["id"]: r.get("text") for r in _rows(f"{RES}/{tag}_think_s{s}.jsonl")},
                 "SB": {r["id"]: r.get("text") for r in _rows(f"{RES}/{tag}_sb_s{s}.jsonl")}}
        fail = set(G.get("_gold_fail", []))
        todo = [((i, a), I[i]["db_id"], I[i]["gold"], extract(x)) for a, R in texts.items() for i, x in R.items()
                if i not in fail and a not in G.get(i, {})]
        todo.sort(key=lambda t: t[2])   # one worker meets the same gold query in a row (its cache)
        with ProcessPoolExecutor(workers) as ex:
            for n, fu in enumerate(as_completed([ex.submit(grade, *t) for t in todo]), 1):
                (i, a), g = fu.result()
                if g is None:
                    fail.add(i); G.pop(i, None)
                else:
                    G.setdefault(i, {})[a] = g
                if n % 500 == 0:
                    json.dump({**G, "_gold_fail": sorted(fail)}, open(gp, "w"))
        for i in fail:
            G.pop(i, None)
        G["_gold_fail"] = sorted(fail)
        json.dump(G, open(gp, "w"))
        for a in texts:
            v = [G[i][a] for i in G if i != "_gold_fail" and a in G[i]]
            print(tag, s, a, f"n {len(v)} ok {sum(x['ok'] for x in v)} chk {sum(x['chk'] == 'pass' for x in v)} "
                  f"leak {sum(x['chk'] == 'pass' and not x['ok'] for x in v)}", flush=True)
        print(tag, s, "gold queries that fail:", len(fail), flush=True)


if __name__ == "__main__":
    main()
