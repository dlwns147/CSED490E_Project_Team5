"""MT (docs/prereg/PREREG_MT.md): write BFCL v4's multi-turn items to $POC_DATA/bfcl/mt_items.jsonl ({id, cat, system, turns,
initial_config, involved_classes, ground_truth}). The prompt is BFCL's prompt mode for open models, built with its own code
(load_dataset_entry: the involved classes' function docs; system_prompt_pre_processing_chat_model: its default system prompt), as
prep_tc.py; turns = the user messages of each turn (a question's own system turn, if any, is merged into the system prompt as BFCL
does). Runs on the login node in the grader venv:
  /home1/leesangjun/venvs/bfcl/bin/python poc/prep_mt.py [category ...]   (default multi_turn_base)"""
import json, os, sys

from bfcl_eval.model_handler.utils import system_prompt_pre_processing_chat_model
from bfcl_eval.utils import load_dataset_entry, load_ground_truth_entry

OUT = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl")


def main():
    cats = sys.argv[1:] or ["multi_turn_base"]
    rows = []
    for c in cats:
        G = {g["id"]: g["ground_truth"] for g in load_ground_truth_entry(c)}
        for e in load_dataset_entry(c):
            assert not e.get("missed_function"), "holdout categories are not supported"
            q = [list(t) for t in e["question"]]
            q[0] = system_prompt_pre_processing_chat_model(q[0], e["function"], e["id"])
            system = q[0].pop(0)["content"]
            rows.append({"id": e["id"], "cat": c, "system": system, "turns": q, "initial_config": e.get("initial_config", {}),
                         "involved_classes": e["involved_classes"], "ground_truth": G[e["id"]]})
    with open(f"{OUT}/mt_items.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} items -> {OUT}/mt_items.jsonl; turns per item {sum(len(r['turns']) for r in rows) / len(rows):.2f}; "
          f"ground-truth calls per item {sum(len(c) for r in rows for c in r['ground_truth']) / len(rows):.2f}")


if __name__ == "__main__":
    main()
