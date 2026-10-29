"""SQL-1 (docs/prereg/PREREG_SQL.md): items for text-to-SQL from BIRD dev, corrected release 2025-11-06 (birdsql/bird_sql_dev_20251106,
raw/dev_20251106.json) on the SQLite databases of BIRD's dev.zip (2024-06-27, extracted to $POC_DATA/bird/dev_databases). Prompt as
Rajkumar et al. (2204.00498): each table's CREATE TABLE statement and its first three rows (values cut at 50 characters), then the
evidence and the question. Writes $POC_DATA/bird/sql_items.jsonl: id, db_id, difficulty, user (the prompt), gold (the gold query).
Also the query extraction, the read-only execution and the free check shared by run_sql.py and grade_sql.py (no client imports).
usage: python prep_sql.py"""
import json, os, re, sqlite3, time

DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bird")
ASK = "Write one SQLite query that answers the question. Return only the query in a ```sql block."


def db_path(db):
    return f"{DATA}/dev_databases/{db}/{db}.sqlite"


def extract(text):
    """the query: the last ```sql block (else the last ``` block, else the text from the first SELECT / WITH); of several statements the
    last that starts with SELECT or WITH"""
    b = re.findall(r"```sql\s*\n?(.*?)```", text or "", re.S | re.I) or re.findall(r"```\w*\s*\n?(.*?)```", text or "", re.S)
    q = b[-1] if b else (lambda m: (text or "")[m.start():] if m else "")(re.search(r"\b(SELECT|WITH)\b", text or "", re.I))
    st = [s.strip() for s in q.split(";") if re.match(r"\s*(SELECT|WITH)\b", s, re.I)]
    return st[-1] if st else q.strip().rstrip(";")


def execute(db, sql, timeout=30.0):
    """(rows, error): the query on the database, read-only, stopped after `timeout` seconds (error 'timeout')"""
    if not sql.strip():
        return None, "no query"
    con = sqlite3.connect(f"file:{db_path(db)}?mode=ro&immutable=1", uri=True)
    end = time.time() + timeout
    con.set_progress_handler(lambda: time.time() > end, 10000)
    try:
        return con.execute(sql).fetchall(), None
    except Exception as e:
        return None, "timeout" if time.time() > end else f"{type(e).__name__}: {e}"[:300]
    finally:
        con.close()


def check(db, sql):
    """the free check: 'pass' (runs, at least one row), else what it saw (the error, or 'no rows')"""
    rows, err = execute(db, sql)
    return "pass" if err is None and rows else (err or "no rows")


def schema(db):
    con = sqlite3.connect(f"file:{db_path(db)}?mode=ro&immutable=1", uri=True)   # immutable: no lock files on the shared file system
    out = []
    for name, sql in con.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name != 'sqlite_sequence'"):
        cur = con.execute(f'SELECT * FROM "{name}" LIMIT 3')
        cols = [d[0] for d in cur.description]
        rows = ["\t".join(str(v)[:50] for v in r) for r in cur.fetchall()]
        out.append(f"{sql.strip()}\n/*\n3 example rows:\nSELECT * FROM \"{name}\" LIMIT 3;\n" + "\t".join(cols) + "\n" + "\n".join(rows) + "\n*/")
    con.close()
    return "\n\n".join(out)


def main():
    Q = json.load(open(f"{DATA}/raw/dev_20251106.json"))
    S = {db: schema(db) for db in sorted({q["db_id"] for q in Q})}
    with open(f"{DATA}/sql_items.jsonl", "w") as f:
        for q in Q:
            ev = (q.get("evidence") or "").strip()
            user = f"{S[q['db_id']]}\n\n-- External knowledge: {ev}\n-- Question: {q['question'].strip()}\n\n{ASK}"
            f.write(json.dumps({"id": str(q["question_id"]), "db_id": q["db_id"], "difficulty": q["difficulty"], "user": user,
                                "gold": q["SQL"]}) + "\n")
    print(len(Q), "items;", {db: len(s) // 4 for db, s in S.items()}, "(schema, ~tokens)")


if __name__ == "__main__":
    main()
