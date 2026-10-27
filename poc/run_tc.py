"""TC-1 (docs/prereg/PREREG_TC.md): tool calling (BFCL v4 single-turn, prompt mode), where the free check is weak. Per item and seed,
all arms against one server (BFCL's system prompt with the function docs, then the user's request):
  cheap  N = non-thinking calls (2k cap); S = the model's yes / no answer to "would thinking first help you make the right calls?"
  think  T = thinking calls (16k cap)
  sb     SB = thinking cut at 2,000 tokens (budget forcing), then the calls
The free check (schema validation of the decoded calls, no gold), agreement, grading (BFCL's own AST checker) and the policies are
offline: poc/grade_tc.py, poc/analyze_tc.py. Items: $POC_DATA/bfcl/tc_items.jsonl (poc/prep_tc.py). Rows resume.
usage: python run_tc.py <tag> <seed>     (TC_SUBSET=i/k: items i, i+k, ... only — the smoke; TC_ARMS=think: only those arms — SAMP)"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat  # noqa: E402
from run_geo_cross import budget_chat  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl", "tc_items.jsonl")
SELECT = """Here is a request. Before making the function calls for it, decide: would thinking step by step first help you make the \
right calls? Answer with one word, yes or no.

Request:
{q}"""


def main():
    tag, seed = sys.argv[1], int(sys.argv[2])
    P = [json.loads(l) for l in open(DATA)]
    if os.environ.get("TC_SUBSET"):
        i, k = map(int, os.environ["TC_SUBSET"].split("/")); P = P[i::k]
    os.makedirs(RES, exist_ok=True)
    path = {a: f"{RES}/{tag}_{a}_s{seed}.jsonl" for a in ("cheap", "think", "sb")}
    done = {a: {r["id"] for r in _rows(f)} for a, f in path.items()}
    sd = lambda p: seed * 1000 + zlib.crc32(p["id"].encode()) % 997

    def cheap(p):
        n = chat(p["user"], system=p["system"], think=False, max_tokens=2048, temperature=0.7, seed=sd(p))
        d = chat(SELECT.format(q=p["user"]), system=p["system"], think=False, max_tokens=8, temperature=0.7, seed=sd(p))
        return "cheap", {"id": p["id"], "n_text": n["text"], "n_tok": n["out_tokens"], "n_finish": n["finish"],
                         "s_ans": (d["text"] or "").strip().lower()[:20], "s_tok": d["out_tokens"]}

    def think(p):
        o = chat(p["user"], system=p["system"], think=True, max_tokens=16000, temperature=0.7, seed=sd(p))
        return "think", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "finish": o["finish"]}

    def sb(p):
        o = budget_chat(p["user"], 2000, max_tokens=2048, temperature=0.7, seed=sd(p), cut_note="I will now write the function calls.",
                        system=p["system"])
        return "sb", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "think_tokens": o["think_tokens"], "finish": o["finish"]}

    arms = os.environ.get("TC_ARMS", "cheap,think,sb").split(",")
    jobs = [(f, p) for p in P for a, f in (("cheap", cheap), ("think", think), ("sb", sb)) if a in arms and p["id"] not in done[a]]
    out = {a: open(f, "a") for a, f in path.items()}
    with ThreadPoolExecutor(64) as ex:
        for fu in as_completed([ex.submit(f, p) for f, p in jobs]):
            try:
                a, row = fu.result()
                out[a].write(json.dumps(row) + "\n"); out[a].flush()
            except Exception as e:   # as run_if: one failed request must not stop the other rows
                print(tag, seed, "request failed, no row:", repr(e)[:200], flush=True)
    for f in out.values():
        f.close()
    print(tag, seed, {a: len(_rows(f)) for a, f in path.items()}, flush=True)


if __name__ == "__main__":
    main()
