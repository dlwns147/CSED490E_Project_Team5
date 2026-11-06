"""MT (docs/prereg/PREREG_MT.md): write BFCL v4's multi-turn items to $POC_DATA/bfcl/mt_items.jsonl ({id, cat, system, turns,
initial_config, involved_classes, ground_truth}). The prompt is BFCL's prompt mode for open models, built with its own code
(load_dataset_entry: the involved classes' function docs; system_prompt_pre_processing_chat_model: its default system prompt), as
prep_tc.py; turns = the user messages of each turn (a question's own system turn, if any, is merged into the system prompt as BFCL
does). Holdout turns (multi_turn_miss_func) get BFCL's own user message with the held-out function docs (base_handler: the
DEFAULT_USER_PROMPT_FOR_ADDITIONAL_FUNCTION_PROMPTING turn); those docs are absent from the system prompt, as in BFCL. long_context is
left out (its states overflow a 3090's context). Runs on the login node in the grader venv:
  /home1/leesangjun/venvs/bfcl/bin/python poc/prep_mt.py [category ...]   (default multi_turn_base multi_turn_miss_param multi_turn_miss_func)
  --fc (addendum MT-FC): the native function-calling form, all four multi-turn categories, to mt_fc_items.jsonl: no default system
  prompt, the functions as OpenAI tools (BFCL's convert_to_tool); holdout turns keep BFCL's user message, as its local FC handlers do."""
import json, os, sys

from bfcl_eval.constants.default_prompts import DEFAULT_USER_PROMPT_FOR_ADDITIONAL_FUNCTION_PROMPTING
from bfcl_eval.constants.enums import ModelStyle
from bfcl_eval.constants.type_mappings import GORILLA_TO_OPENAPI
from bfcl_eval.model_handler.utils import convert_to_tool, system_prompt_pre_processing_chat_model
from bfcl_eval.utils import load_dataset_entry, load_ground_truth_entry

OUT = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl")


def main():
    fc = "--fc" in sys.argv
    cats = [a for a in sys.argv[1:] if a != "--fc"] or (["multi_turn_base", "multi_turn_miss_param", "multi_turn_miss_func"] + ["multi_turn_long_context"] * fc)
    rows = []
    for c in cats:
        G = {g["id"]: g["ground_truth"] for g in load_ground_truth_entry(c)}
        for e in load_dataset_entry(c):
            q = [list(t) for t in e["question"]]
            for ti, fs in e.get("missed_function", {}).items():
                assert not q[int(ti)], "a holdout turn has no user message"
                q[int(ti)] = [{"role": "user", "content": DEFAULT_USER_PROMPT_FOR_ADDITIONAL_FUNCTION_PROMPTING.format(functions=fs)}]
            if fc:
                system = q[0].pop(0)["content"] if q[0] and q[0][0]["role"] == "system" else None
            else:
                q[0] = system_prompt_pre_processing_chat_model(q[0], e["function"], e["id"])
                system = q[0].pop(0)["content"]
            rows.append({"id": e["id"], "cat": c, "system": system, "turns": q, "initial_config": e.get("initial_config", {}),
                         "involved_classes": e["involved_classes"], "ground_truth": G[e["id"]],
                         **({"tools": convert_to_tool(e["function"], GORILLA_TO_OPENAPI, ModelStyle.OPENAI_COMPLETIONS)} if fc else {})})
    name = "mt_fc_items" if fc else "mt_items"
    with open(f"{OUT}/{name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} items -> {OUT}/{name}.jsonl; turns per item {sum(len(r['turns']) for r in rows) / len(rows):.2f}; "
          f"ground-truth calls per item {sum(len(c) for r in rows for c in r['ground_truth']) / len(rows):.2f}")


if __name__ == "__main__":
    main()
