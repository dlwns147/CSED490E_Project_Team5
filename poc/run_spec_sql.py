"""PREREG_SPEC addendum SQL (2026-11-21): the text-to-SQL specialist Arctic-Text2SQL-R1-7B (Snowflake, arXiv 2505.20315) on our items, with
its own evaluation inputs: OmniSQL's pre-processed prompts (`input_seq` of data/dev_bird.json and data/test_spider.json from
huggingface.co/datasets/seeklhy/OmniSQL-datasets; schema with sampled and question-matched values), greedy decoding as in its paper.
Items are matched to ours by position and question text (Spider test: all 2,147; BIRD dev: the 1,354 questions the 2025-11-06
correction left unchanged; the rest are skipped). Rows go to results/sql/<tag>_cheap_s1.jsonl as an N query, so poc/grade_sql.py grades
them with our gold and free check.
usage: run_spec_sql.py <tag> <omni json> [spider]   (SQL_SPLIT=spider for Spider test items)"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_msgs  # noqa: E402
from prep_sql import ITEMS  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
norm = lambda t: re.sub(r"\s+", " ", t).strip().lower()


def main():
    tag, omni = sys.argv[1], sys.argv[2]
    O = json.load(open(omni)); I = [json.loads(l) for l in open(ITEMS)]
    pairs = []
    for o, it in zip(O, I):
        oq = norm(re.search(r"Question:\n(.*?)\n\nInstructions", o["input_seq"], re.S).group(1))
        iq = norm(re.search(r"-- Question: (.*?)\n\nWrite one", it["user"], re.S).group(1))
        if oq in iq or iq in oq:
            pairs.append((it["id"], o["input_seq"]))
    if os.environ.get("SPEC_SMOKE"):
        pairs = pairs[: int(os.environ["SPEC_SMOKE"])]
    print(tag, "matched", len(pairs), "of", len(I), flush=True)

    def run(p):
        i, prompt = p
        o = chat_msgs([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=8192, seed=1)
        text = o["text"] or ""
        m = re.findall(r"```sql\s*(.*?)```", text, re.S)
        return {"id": i, "n_text": f"```sql\n{m[-1].strip()}\n```" if m else text[-2000:], "n_tok": o["out_tokens"], "n_finish": o["finish"],
                "raw_tail": text[-800:]}

    os.makedirs(RES, exist_ok=True)
    with ThreadPoolExecutor(64) as ex, open(f"{RES}/{tag}_cheap_s1.jsonl", "w") as f:
        for r in ex.map(run, pairs):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main()
