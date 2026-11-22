"""PREREG_SPEC addendum TC (2026-11-22): the tool-calling specialist ToolACE-2-8B (Team-ACE, Llama-3.1-8B fine-tune; its model card's
prompt is BFCL's prompt-mode system prompt, the one our items carry) on our 3,482 BFCL v4 single-turn items, greedy as the BFCL leaderboard
runs it (temperature ~0). Rows go to results/tc/<tag>_cheap_s1.jsonl as an N call (n_text, n_tok), so poc/grade_tc.py grades them
with BFCL's AST checker and our schema check. usage: run_spec_tc.py <tag>"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_msgs  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl", "tc_items.jsonl")


def main():
    tag = sys.argv[1]
    items = [json.loads(l) for l in open(DATA)]
    if os.environ.get("SPEC_SMOKE"):
        items = items[:: max(1, len(items) // int(os.environ["SPEC_SMOKE"]))]
    print(tag, len(items), "items", flush=True)

    def run(x):
        o = chat_msgs([{"role": "system", "content": x["system"]}, {"role": "user", "content": x["user"]}], temperature=0.0, max_tokens=2048, seed=1)
        return {"id": x["id"], "n_text": o["text"] or "", "n_tok": o["out_tokens"], "n_finish": o["finish"]}

    os.makedirs(RES, exist_ok=True)
    with ThreadPoolExecutor(64) as ex, open(f"{RES}/{tag}_cheap_s1.jsonl", "w") as f:
        for r in ex.map(run, items):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main()
