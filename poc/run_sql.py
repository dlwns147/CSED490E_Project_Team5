"""SQL-1 (docs/prereg/PREREG_SQL.md): text-to-SQL on BIRD dev (corrected 2025-11-06), where the free check is running the query (no
error within 30 s, at least one row) and the evidence (BIRD's domain definitions) is always in the prompt. Per question and seed, all
arms against one server:
  cheap  N = non-thinking query (2k cap); S = the model's yes / no answer to "would thinking step by step first help?"; R = only where
         N fails the check, one non-thinking rewrite given N's query and what the check saw (2k cap)
  think  T = thinking query (cap SQL_TK, default 16,000)
  sb     SB = thinking cut at 2,000 tokens (budget forcing), then the query (2k cap)
The check on T / SB, the grade (BIRD's execution accuracy) and the policies are offline: poc/grade_sql.py, poc/analyze_sql.py.
Items: $POC_DATA/bird/sql_items.jsonl (poc/prep_sql.py). Rows resume. SQL-F: SQL_FACT=card | lib | both adds the fact to every arm's
prompt (poc/fact_sql.py; lib / both: SQL_LIB=<SQL-1 tag> whose seed s' cheap rows give the library; SQL-FA: SQL_LIB_ADMIT=agree | right | wrong).
SQL-DV: SQL_VIEW=shuffle (the schema's tables in a per-question random order) | plan (a one-line plan comment before the query) changes
the prompt of every arm; arm quick = N alone (no S / R), written to the cheap file. XG (gpt-oss as the generator): POC_HARMONY=1 makes SB
the medium-effort think cut at 2,000 (harmony_budget_chat, as LC-OSS) and skips S; the effort of N / R / T is POC_REASONING_EFFORT.
usage: python run_sql.py <tag> <seed>     (SQL_SUBSET=i/k: questions i, i+k, ... only — the smoke; SQL_ARMS=think: only those arms;
  SQL_SPLIT=train: BIRD train's items, CV-1; SQL_IDS=<file>: only those ids)"""
import json, os, random, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, chat_msgs  # noqa: E402
from fact_sql import library, with_fact  # noqa: E402
from prep_sql import ASK, DATA, ITEMS, check, extract  # noqa: E402
from run_geo_cross import budget_chat, harmony_budget_chat  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
TK = int(os.environ.get("SQL_TK", 16000))
POOL = int(os.environ.get("SQL_POOL", 64))
HARMONY = bool(os.environ.get("POC_HARMONY"))   # XG: gpt-oss as the generator (SB as LC-OSS; S not asked)
SELECT = """Here is a text-to-SQL question.

{q}

Do not write the query yet. Decide only: would thinking step by step first help you write a correct query for it? Answer with \
one word, yes or no."""
REPAIR = "Running this query on the database {what}. Write a corrected SQLite query. Return only the query in a ```sql block."
PLAN = ("Write one SQLite query that answers the question: first a comment line `-- plan: <the tables to join> -> <the output columns>`, "
        "then the query, both in one ```sql block.")


def view(user, how, seed):
    """SQL-DV: the same question seen differently (None: unchanged)"""
    if how == "shuffle":
        head, tail = user.split("\n\n-- External knowledge:", 1)
        blocks = head.split("\n\nCREATE TABLE")
        blocks = [blocks[0]] + ["CREATE TABLE" + b for b in blocks[1:]]
        random.Random(seed).shuffle(blocks)
        return "\n\n".join(blocks) + "\n\n-- External knowledge:" + tail
    if how == "plan":
        assert ASK in user
        return user.replace(ASK, PLAN)
    return user


def main():
    tag, seed = sys.argv[1], int(sys.argv[2])
    P = [json.loads(l) for l in open(ITEMS)]
    fact = os.environ.get("SQL_FACT")
    if fact:   # the library is built over all questions, before the subset
        lib = library(P, os.environ["SQL_LIB"], seed, admit=os.environ.get("SQL_LIB_ADMIT", "check")) if fact in ("lib", "both") else None
        P = [{**p, "user": with_fact(p, fact, lib)} for p in P]
    if os.environ.get("SQL_SUBSET"):
        i, k = map(int, os.environ["SQL_SUBSET"].split("/")); P = P[i::k]
    if os.environ.get("SQL_IDS"):   # CV-1: only the question ids in this file (one per line), e.g. the retry thinks
        keep = set(open(os.environ["SQL_IDS"]).read().split()); P = [p for p in P if p["id"] in keep]
    os.makedirs(RES, exist_ok=True)
    if os.environ.get("SQL_VIEW"):
        P = [dict(p, user=view(p["user"], os.environ["SQL_VIEW"], seed * 1000 + zlib.crc32(p["id"].encode()) % 997)) for p in P]
    arms = os.environ.get("SQL_ARMS", "cheap,think,sb").split(",")
    path = {a: f"{RES}/{tag}_{a}_s{seed}.jsonl" for a in ("cheap", "think", "sb")}
    done = {a: {r["id"] for r in _rows(f)} for a, f in path.items()}
    sd = lambda p: seed * 1000 + zlib.crc32(p["id"].encode()) % 997

    def cheap(p):
        n = chat(p["user"], think=False, max_tokens=2048, temperature=0.7, seed=sd(p))
        d = ({"text": "", "out_tokens": 0} if HARMONY else
             chat(SELECT.format(q=p["user"].replace(ASK, "").strip()), think=False, max_tokens=8, temperature=0.7, seed=sd(p)))
        c = check(p["db_id"], extract(n["text"]))
        row = {"id": p["id"], "n_text": n["text"], "n_tok": n["out_tokens"], "n_finish": n["finish"], "c_n": c,
               "s_ans": (d["text"] or "").strip().lower()[:20], "s_tok": d["out_tokens"]}
        if c != "pass":
            what = "returned no rows" if c == "no rows" else "stopped after 30 seconds" if c == "timeout" else f"gave the error: {c}"
            r = chat_msgs([{"role": "user", "content": p["user"]}, {"role": "assistant", "content": n["text"]},
                           {"role": "user", "content": REPAIR.format(what=what)}], think=False, max_tokens=2048, temperature=0.7, seed=sd(p))
            row.update(r_text=r["text"], r_tok=r["out_tokens"], r_finish=r["finish"])
        return "cheap", row

    def quick(p):   # SQL-DV: N alone
        n = chat(p["user"], think=False, max_tokens=2048, temperature=0.7, seed=sd(p))
        return "cheap", {"id": p["id"], "n_text": n["text"], "n_tok": n["out_tokens"], "n_finish": n["finish"],
                         "c_n": check(p["db_id"], extract(n["text"]))}

    def think(p):
        o = chat(p["user"], think=True, max_tokens=TK, temperature=0.7, seed=sd(p))
        return "think", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "finish": o["finish"]}

    def sb(p):
        o = (harmony_budget_chat if HARMONY else budget_chat)(p["user"], 2000, max_tokens=2048, temperature=0.7, seed=sd(p),
                                                              cut_note="I will now write the query.")
        return "sb", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "think_tokens": o["think_tokens"], "finish": o["finish"]}

    jobs = [(f, p) for p in P for a, f in (("cheap", cheap), ("think", think), ("sb", sb), ("quick", quick)) if a in arms
            and p["id"] not in done["cheap" if a == "quick" else a]]
    out = {a: open(f, "a") for a, f in path.items()}
    with ThreadPoolExecutor(POOL) as ex:
        for fu in as_completed([ex.submit(f, p) for f, p in jobs]):
            try:
                a, row = fu.result()
                out[a].write(json.dumps(row) + "\n"); out[a].flush()
            except Exception as e:   # as run_lcb: one failed request must not stop the other rows
                print(tag, seed, "request failed, no row:", repr(e)[:200], flush=True)
    for f in out.values():
        f.close()
    print(tag, seed, {a: len(_rows(f)) for a, f in path.items()}, flush=True)


if __name__ == "__main__":
    main()
