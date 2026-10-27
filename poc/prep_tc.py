"""TC-1 (docs/prereg/PREREG_TC.md): write the tool-calling items from BFCL v4 (pip package bfcl-eval 2026.3.23, Apache-2.0) to
$POC_DATA/bfcl/tc_items.jsonl ({id, cat, system, user, functions}) and their answers to tc_answers.jsonl ({id, cat, ground_truth}).
The prompt is BFCL's own prompt mode for open models (its default system prompt with the function docs in JSON; calls returned as
[func(arg=value), ...]), built with its code. Single-turn Python categories, every item (the every-3rd subset of live_multiple and
live_irrelevance planned for cost was dropped after the smoke, PREREG_TC.md); items whose question is not one user turn (after an optional system
turn) are left out. Runs on the login node in the grader venv:
  /home1/leesangjun/venvs/bfcl/bin/python poc/prep_tc.py"""
import json, os

from bfcl_eval.model_handler.utils import system_prompt_pre_processing_chat_model
import bfcl_eval

SRC = os.path.join(os.path.dirname(bfcl_eval.__file__), "data")
OUT = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl")
CATS = ("simple_python", "multiple", "parallel", "parallel_multiple", "irrelevance",
        "live_simple", "live_multiple", "live_parallel", "live_parallel_multiple", "live_irrelevance", "live_relevance")
THIRD = ()   # was ("live_multiple", "live_irrelevance"): every 3rd item only; dropped after the smoke (thinks are short)


def main():
    os.makedirs(OUT, exist_ok=True)
    items, answers = [], []
    for c in CATS:
        R = [json.loads(l) for l in open(f"{SRC}/BFCL_v4_{c}.json")]
        A = {}
        if os.path.exists(f"{SRC}/possible_answer/BFCL_v4_{c}.json"):
            A = {a["id"]: a["ground_truth"] for a in (json.loads(l) for l in open(f"{SRC}/possible_answer/BFCL_v4_{c}.json"))}
        for i, r in enumerate(R):
            if c in THIRD and i % 3:
                continue
            q = [dict(m) for m in r["question"][0]]
            if [m["role"] for m in q] not in (["user"], ["system", "user"]):
                continue
            msgs = system_prompt_pre_processing_chat_model(q, r["function"], r["id"])
            items.append({"id": r["id"], "cat": c, "system": msgs[0]["content"], "user": msgs[1]["content"], "functions": r["function"]})
            answers.append({"id": r["id"], "cat": c, "ground_truth": A.get(r["id"])})
    with open(f"{OUT}/tc_items.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in items)
    with open(f"{OUT}/tc_answers.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in answers)
    n = {}
    for x in items:
        n[x["cat"]] = n.get(x["cat"], 0) + 1
    print(len(items), n)


if __name__ == "__main__":
    main()
