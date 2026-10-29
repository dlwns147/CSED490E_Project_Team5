"""SQL-F (docs/prereg/PREREG_SQL.md, addendum SQL-F): the fact for text-to-SQL, added to run_sql.py's prompt between the schema and
the evidence (SQL_FACT=card | lib | both).
  card  a few lines of SQLite usage (written from SQLite's documentation of its dialect, before SQL-F's rows)
  lib   the model's own queries for the 3 most similar other questions on the same database (word overlap of the questions) that
        passed the free check in SQL-1, from seed s' = s mod 3 + 1 (no labels: only the check)
usage: python fact_sql.py <lib tag> <seed> [id]   (prints one question's prompt, the smoke)"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prep_sql import ASK, DATA  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
CARD = """-- SQLite notes: quote a table or column name that contains spaces or symbols with backticks (`Order Date (UTC)`); write string
-- values in single quotes ('O''Brien'); dates are text, so use STRFTIME('%Y', col) or SUBSTR(col, 1, 4), not YEAR() or MONTH();
-- integer division truncates, so use CAST(x AS REAL) / y for ratios and percentages; return only the columns the question asks for."""
LIB_HEAD = "-- Questions on this database and queries for them that ran and returned rows (written earlier, not verified):"
K = 3


def question(user):
    return user.split("-- Question:", 1)[1].replace(ASK, "").strip()


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def library(items, tag, seed, k=K):
    """{id: [(question, query), ...]}: per question, the k most similar other questions on its database whose SQL-1 query (seed s')
    passed the check"""
    from prep_sql import extract
    s2 = seed % 3 + 1
    rows = {r["id"]: r for r in map(json.loads, open(f"{RES}/{tag}_cheap_s{s2}.jsonl"))}
    pool = {}
    for p in items:
        r = rows.get(p["id"])
        if r and r["c_n"] == "pass":
            pool.setdefault(p["db_id"], []).append((p["id"], question(p["user"]), extract(r["n_text"])))
    out = {}
    for p in items:
        q = words(question(p["user"]))
        cand = [(len(q & words(x)) / max(1, len(q | words(x))), j, x, s) for j, x, s in pool.get(p["db_id"], []) if j != p["id"]]
        cand.sort(key=lambda c: (-c[0], int(c[1])))
        out[p["id"]] = [(x, s) for _, _, x, s in cand[:k]]
    return out


def with_fact(p, fact, lib=None):
    """the prompt with the fact between the schema and the evidence"""
    head, tail = p["user"].split("\n\n-- External knowledge:", 1)
    add = []
    if fact in ("card", "both"):
        add.append(CARD)
    if fact in ("lib", "both") and lib and lib.get(p["id"]):
        add.append(LIB_HEAD + "\n" + "\n".join(f"-- Question: {x}\n```sql\n{s}\n```" for x, s in lib[p["id"]]))
    return head + "\n\n" + "\n\n".join(add) + "\n\n-- External knowledge:" + tail


if __name__ == "__main__":
    P = [json.loads(l) for l in open(f"{DATA}/sql_items.jsonl")]
    L = library(P, sys.argv[1], int(sys.argv[2]))
    p = next(p for p in P if p["id"] == (sys.argv[3] if len(sys.argv) > 3 else P[0]["id"]))
    print(with_fact(p, "both", L)[-2500:])
    print("questions with fewer than", K, "examples:", sum(len(v) < K for v in L.values()), "of", len(L))
