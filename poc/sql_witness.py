# SIDE-W (docs/prereg/PREREG_SIDE.md): a small distinguishing sub-database ("witness") for two SQLite queries whose
# results differ on the real database, found by delta debugging (Zeller & Hildebrandt 2002, ddmin's complement steps) over the rows of
# the tables either query names. The rows live in TEMP tables created from the original DDL, which shadow the main ones (SQLite resolves
# an unqualified name in temp first), so the queries run unchanged; declared foreign keys are closed after every deletion (orphans
# removed to a fixpoint) so that a witness never relies on a dangling reference. Sound by construction: the two queries return
# different row sets (the graders' comparison) on the witness, and the witness is a subset of the real database.
# usage (a CPU job; a few pairs on the login node): python poc/sql_witness.py <requests.jsonl> <out.jsonl> [max_pairs] [workers]
#   requests: rows with sset (dev / spider / spiderdev / fresh = BIRD train), id, text, text2 (results/conf/sel_req_pw.jsonl, or the
#   training pairs from nlp_data/scratch/wit_req_train.jsonl); out: one row per unordered pair, key = [sset, id, query a, query b] sorted
import json, os, re, sqlite3, sys, time
from concurrent.futures import ProcessPoolExecutor

PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
SETS = {"dev": ("sql_items", "dev_databases"), "spider": ("sql_spider_items", "spider_databases"),
        "spiderdev": ("sql_spiderdev_items", "spiderdev_databases"), "fresh": ("sql_train_items", "train_databases")}
QT, MAXT, MAXS = 5.0, 600, 120.0   # per-query timeout (s), tests and seconds per pair
FK = os.environ.get("WIT_FK", "1") == "1"   # 0: the second pass for pairs whose results differ only through dangling references (the
#   real database has orphans, and closing the keys removes the difference): no closure, the witness keeps the real orphans it needs


def sig(res):
    """what the free check and a reader see of a result besides its values: empty or not, any NULL cell; a witness keeps both as on
    the real database (else the smallest witness is often the empty database, where COUNT gives 0 and SUM gives NULL)"""
    return None if res is None else (len(res) > 0, any(v is None for r in res for v in r))


class Witness:
    def __init__(self, path, qa, qb):
        self.con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, isolation_level=None)
        self.con.execute("PRAGMA temp_store=MEMORY")
        self.qa, self.qb, self.tests = qa, qb, 0
        self.sig = (sig(self.run(qa)), sig(self.run(qb)))   # on the real database, before the temp tables shadow it
        ddl = dict(self.con.execute("select name, sql from sqlite_master where type='table' and name not like 'sqlite_%'").fetchall())
        text = (qa + " " + qb).lower()
        self.tabs = [t for t in ddl if re.search(r"(?<!\w)" + re.escape(t.lower()) + r"(?!\w)", text)]
        for t in self.tabs:
            s = re.sub(r"^\s*CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?", "CREATE TEMP TABLE ", ddl[t], count=1, flags=re.I)
            s = re.sub(r"\)\s*WITHOUT\s+ROWID\s*;?\s*$", ")", s, flags=re.I)
            self.con.execute(s)
        self.fks = []
        for t in self.tabs:
            for f in self.con.execute(f'PRAGMA main.foreign_key_list("{t}")').fetchall():
                ref = next((x for x in self.tabs if x.lower() == f[2].lower()), None)
                if ref and f[3] and f[4]:
                    self.fks.append((t, f[3], ref, f[4]))

    def run(self, q):
        end = time.time() + QT
        self.con.set_progress_handler(lambda: time.time() > end, 10000)
        try:
            return frozenset(self.con.execute(q).fetchall())
        except Exception:
            return None
        finally:
            self.con.set_progress_handler(None, 0)

    def differ(self):
        self.tests += 1
        a = self.run(self.qa)
        if a is None:
            return False
        b = self.run(self.qb)
        return b is not None and a != b and (sig(a), sig(b)) == self.sig

    def close_fk(self):
        if not FK:
            return
        for _ in range(20):
            n = 0
            for t, c, ref, rc in self.fks:
                try:
                    n += self.con.execute(f'DELETE FROM temp."{t}" WHERE "{c}" IS NOT NULL AND "{c}" NOT IN '
                                          f'(SELECT "{rc}" FROM temp."{ref}" WHERE "{rc}" IS NOT NULL)').rowcount
                except sqlite3.OperationalError:
                    pass
            if n == 0:
                return

    def load(self):
        """fill the temp tables with a deterministic sample of each table's rows (rowid hash), growing 1/4096 -> all until the results
        differ: a large table is copied whole only when no sample separates the queries"""
        size = {t: self.con.execute(f'SELECT COUNT(*) FROM main."{t}"').fetchone()[0] for t in self.tabs}
        big = max(size.values(), default=0)
        for frac in (1 / 4096, 1 / 512, 1 / 64, 1 / 8, 1):
            if frac < 1 and big * frac < 64:
                continue
            for t in self.tabs:
                self.con.execute(f'DELETE FROM temp."{t}"')
                try:
                    cond = "" if frac == 1 else f" WHERE ((rowid * 2654435761) % 1000003) < {int(frac * 1000003)}"
                    self.con.execute(f'INSERT INTO temp."{t}" SELECT * FROM main."{t}"{cond}')
                except sqlite3.OperationalError:   # no rowid in main: the whole table
                    self.con.execute(f'INSERT INTO temp."{t}" SELECT * FROM main."{t}"')
            self.close_fk()
            if self.differ():
                return True
        return False

    def units(self):
        return [(t, r) for t in self.tabs for (r,) in self.con.execute(f'SELECT rowid FROM temp."{t}" ORDER BY rowid')]

    def try_delete(self, chunk):
        """delete the chunk (contiguous in (table, rowid) order: one rowid range per table), close the keys, keep it if the results
        still differ"""
        self.con.execute("SAVEPOINT s")
        rng = {}
        for t, r in chunk:
            lo, hi = rng.get(t, (r, r))
            rng[t] = (min(lo, r), max(hi, r))
        for t, (lo, hi) in rng.items():
            self.con.execute(f'DELETE FROM temp."{t}" WHERE rowid BETWEEN ? AND ?', (lo, hi))
        self.close_fk()
        if self.differ():
            self.con.execute("RELEASE s"); return True
        self.con.execute("ROLLBACK TO s"); self.con.execute("RELEASE s"); return False

    def shrink(self):
        t0 = time.time()
        if not self.load():
            return "no difference on the database with its foreign keys closed"
        U, n = self.units(), 2
        while len(U) > 1 and self.tests < MAXT and time.time() - t0 < MAXS:
            k = -(-len(U) // n)
            for j in range(0, len(U), k):
                if self.tests >= MAXT or time.time() - t0 >= MAXS:
                    break
                if self.try_delete(U[j:j + k]):
                    U, n = self.units(), max(n - 1, 2)
                    break
            else:
                if n >= len(U):
                    return "1-minimal"
                n = min(2 * n, len(U))
        return "1-minimal" if len(U) <= 1 else "budget"

    def dump(self):
        out = {}
        for t in self.tabs:
            cur = self.con.execute(f'SELECT * FROM temp."{t}"')
            rows = cur.fetchall()
            if rows:
                out[t] = {"cols": [d[0] for d in cur.description], "rows": [[None if v is None else str(v)[:60] for v in r] for r in rows[:50]],
                          "n": len(rows)}
        res = {}
        for k, q in (("a", self.qa), ("b", self.qb)):
            cur = self.con.execute(q)
            rows = cur.fetchall()
            res[k] = {"cols": [d[0] for d in cur.description or []], "rows": [[None if v is None else str(v)[:60] for v in r] for r in rows[:10]],
                      "n": len(rows)}
        return out, res


def wkey(sset, i, qa, qb):
    a, b = sorted((qa, qb))
    return json.dumps([sset, i, a, b])


def wload():
    """{key: witness row} from $PW_WITNESS (comma-separated files under the repo's results/sqlwit/), or {} when it is unset"""
    W = {}
    for f in filter(None, os.environ.get("PW_WITNESS", "").split(",")):
        for l in open(f):
            r = json.loads(l)
            if r.get("status") in ("1-minimal", "budget"):
                W[r["key"]] = r
    return W


def wtext(w, qa, qb, rows=12, res=5):
    """the witness as the pairwise prompt shows it after both queries (A = qa): each table's columns that either query names (else
    its first three), up to `rows` rows, values cut at 40 characters, then each query's result on these rows"""
    a, b = sorted((qa, qb))
    ra, rb = (w["res"]["a"], w["res"]["b"]) if qa == a else (w["res"]["b"], w["res"]["a"])
    text = (qa + " " + qb).lower()
    cut = lambda v: "NULL" if v is None else str(v)[:40]
    out = ["A small part of the database on which the two queries return different results:"]
    for t, v in w["tables"].items():
        keep = [j for j, c in enumerate(v["cols"]) if re.search(r"(?<!\w)" + re.escape(c.lower()) + r"(?!\w)", text)] or [0, 1, 2][:len(v["cols"])]
        out.append(f"Table {t} ({v['n']} row{'' if v['n'] == 1 else 's'}):\n" + "\t".join(v["cols"][j] for j in keep) + "\n"
                   + "\n".join("\t".join(cut(r[j]) for j in keep) for r in v["rows"][:rows]))
    for t, x in (("A", ra), ("B", rb)):
        out.append(f"On these rows query {t} returns {x['n']} row{'' if x['n'] == 1 else 's'}:\n" + "\t".join(x["cols"])[:300] + "\n"
                   + "\n".join("\t".join(cut(v) for v in r)[:300] for r in x["rows"][:res]))
    return "\n\n".join(out)


def one(job):
    key, path, qa, qb = job
    t0 = time.time()
    try:
        w = Witness(path, qa, qb)
        st = w.shrink()
        tabs, res = w.dump() if st in ("1-minimal", "budget") else ({}, {})
        return {"key": key, "status": st, "tests": w.tests, "sec": round(time.time() - t0, 1), "tables": tabs, "res": res,
                "rows": sum(v["n"] for v in tabs.values())}
    except Exception as e:
        return {"key": key, "status": f"error {type(e).__name__}: {e}"[:200], "sec": round(time.time() - t0, 1)}


def main():
    src, out = sys.argv[1], sys.argv[2]
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    items = {}
    for sset, (f, _) in SETS.items():
        for l in open(f"{PD}/bird/{f}.jsonl"):
            r = json.loads(l)
            items[(sset, r["id"])] = r["db_id"]
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["key"] for l in open(out)}
    jobs, seen = [], set()
    for l in open(src):
        r = json.loads(l)
        a, b = sorted((r["text"], r["text2"]))
        key = json.dumps([r["sset"], r["id"], a, b])
        if key in seen or key in done:
            continue
        seen.add(key)
        db = items[(r["sset"], r["id"])]
        jobs.append((key, f"{PD}/bird/{SETS[r['sset']][1]}/{db}/{db}.sqlite", a, b))
    jobs = jobs[:mx or len(jobs)]
    print(f"{len(jobs)} unordered pairs to do ({len(done)} done)", flush=True)
    with open(out, "a") as f, ProcessPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(one, jobs, chunksize=1)):
            f.write(json.dumps(r) + "\n"); f.flush()
            if i % 50 == 0:
                print(i, r["status"], r.get("rows"), r.get("tests"), r["sec"], flush=True)


if __name__ == "__main__":
    main()
