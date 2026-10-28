"""LC-1 (docs/prereg/PREREG_LC.md): code generation (LiveCodeBench, problems from 2025 on), where the free check is the problem's own
sample tests and full thinks are long. Per problem and seed, all arms against one server (LiveCodeBench's generic prompt):
  cheap  N = non-thinking program (4k cap); S = the model's yes / no answer to "would thinking first help you write a correct program?"
  think  T = thinking program (cap LCB_TK, default 32,000: HO-CC's 16k cap left most contest thinks without a program)
  sb     SB = thinking cut at 2,000 tokens (budget forcing), then the program (4k cap)
The free check (the sample tests), the grade (the official LiveCodeBench grader on sample + hidden tests) and the policies are
offline: poc/grade_lcb.py, poc/analyze_lcb.py. Items: $POC_DATA/lcb/lcb_items.jsonl (poc/prep_lcb.py). Rows resume.
usage: python run_lcb.py <tag> <seed>     (LCB_SUBSET=i/k: problems i, i+k, ... only — the smoke; LCB_ARMS=think: only those arms)
gpt-oss (LC-OSS, PREREG_LC.md addendum): POC_HARMONY=1 makes SB the medium-effort think cut at 2,000 (harmony_budget_chat) and skips S
(no non-thinking mode to ask); LCB_EFFORTS=low,medium,high sets the reasoning effort of N, T and the extra arm thinkh (TH, high effort,
cap LCB_TK; LCB_ARMS=cheap,think,sb,thinkh). The 64k rerun (mid-run rule): LCB_ARMS=thinkh LCB_TK=64000 LCB_TH_NAME=thinkh64.
LC-1 cap rule (Qwen3.5-9B's think at 64k): LCB_ARMS=think LCB_TK=64000 LCB_T_NAME=think64 (rows {tag}_think64)."""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat  # noqa: E402
from run_geo_cross import budget_chat, harmony_budget_chat  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "lcb")
DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "lcb", "lcb_items.jsonl")
TK = int(os.environ.get("LCB_TK", 32000))
EN, ET, EH = (os.environ["LCB_EFFORTS"].split(",") if os.environ.get("LCB_EFFORTS") else (None, None, None))
HARMONY = bool(os.environ.get("POC_HARMONY"))
TN = os.environ.get("LCB_T_NAME", "think")   # the think arm's rows (think64: the same arm at a 64k cap)
TH = os.environ.get("LCB_TH_NAME", "thinkh")   # the high-effort arm's rows (thinkh64: the same arm at a 64k cap)
SELECT = """Here is a programming problem.

{q}

Do not write the program yet. Decide only: would thinking step by step first help you write a correct program for it? Answer with \
one word, yes or no."""   # smoke (PREREG_LC.md): with the problem last, its format line made the model start the program instead


def main():
    tag, seed = sys.argv[1], int(sys.argv[2])
    P = [json.loads(l) for l in open(DATA)]
    if os.environ.get("LCB_SUBSET"):
        i, k = map(int, os.environ["LCB_SUBSET"].split("/")); P = P[i::k]
    os.makedirs(RES, exist_ok=True)
    arms = os.environ.get("LCB_ARMS", "cheap,think,sb").split(",")
    path = {a: f"{RES}/{tag}_{ {'thinkh': TH, 'think': TN}.get(a, a)}_s{seed}.jsonl" for a in ("cheap", "think", "sb", "thinkh")
            if a != "thinkh" or a in arms}
    done = {a: {r["id"] for r in _rows(f)} for a, f in path.items()}
    sd = lambda p: seed * 1000 + zlib.crc32(p["id"].encode()) % 997

    def cheap(p):
        n = chat(p["user"], system=p["system"], think=False, max_tokens=4096, temperature=0.7, seed=sd(p), effort=EN)
        d = ({"text": "", "out_tokens": 0} if HARMONY else
             chat(SELECT.format(q=p["user"].split("### Format:")[0].strip()), think=False, max_tokens=8, temperature=0.7, seed=sd(p)))
        return "cheap", {"id": p["id"], "n_text": n["text"], "n_tok": n["out_tokens"], "n_finish": n["finish"],
                         "s_ans": (d["text"] or "").strip().lower()[:20], "s_tok": d["out_tokens"]}

    def think(p, arm="think", effort=ET):
        o = chat(p["user"], system=p["system"], think=True, max_tokens=TK, temperature=0.7, seed=sd(p), effort=effort)
        return arm, {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "finish": o["finish"],
                     **{k: o[k] for k in ("empty_tail", "tool_calls") if k in o}}

    def thinkh(p):
        return think(p, "thinkh", EH)   # written to path["thinkh"], i.e. the TH file

    def sb(p):
        o = (harmony_budget_chat(p["user"], 2000, max_tokens=4096, temperature=0.7, seed=sd(p), system=p["system"]) if HARMONY else
             budget_chat(p["user"], 2000, max_tokens=4096, temperature=0.7, seed=sd(p), cut_note="I will now write the program.",
                         system=p["system"]))
        return "sb", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "think_tokens": o["think_tokens"], "finish": o["finish"]}

    jobs = [(f, p) for p in P for a, f in (("cheap", cheap), ("think", think), ("sb", sb), ("thinkh", thinkh))
            if a in arms and p["id"] not in done[a]]
    out = {a: open(f, "a") for a, f in path.items()}
    with ThreadPoolExecutor(64) as ex:
        for fu in as_completed([ex.submit(f, p) for f, p in jobs]):
            try:
                a, row = fu.result()
                out[a].write(json.dumps(row) + "\n"); out[a].flush()
            except Exception as e:   # as run_tc: one failed request must not stop the other rows
                print(tag, seed, "request failed, no row:", repr(e)[:200], flush=True)
    for f in out.values():
        f.close()
    print(tag, seed, {a: len(_rows(f)) for a, f in path.items()}, flush=True)


if __name__ == "__main__":
    main()
