"""MCST PAPER2 (PREREG_DIFF addendum MCST, amendment 2026-11-28 13:10 UTC): the authors' harness (2605.08498 repo @ 687a6d5) with ONE change —
a robust reader for tool-call arguments. On our vLLM server (gpt-oss tool parser) 1,430 of 1,929 execute_python calls of the PAPER run reached
their tool with empty arguments: their _parse_tool_arguments returns {} whenever the argument string is not strict JSON, so the code never ran
and 201 of 329 instances hit the 8-round limit (their published OpenRouter run: 9). Reader here: strict JSON as before; else JSON with
strict=False (raw newlines in strings); else, for a non-empty string, the string itself as the code. Repairs are tagged in the logged args
(`_repaired`) and the first 300 characters of every unreadable argument string are kept, so the failure's form is on record. Everything else
(prompt, tools, allow-list, 8 rounds, temperature 0, 38k tokens per call, grading) is the authors' code unchanged.
usage (verifier venv, server with --enable-auto-tool-choice --tool-call-parser openai):
  WANDB_MODE=disabled MCNST_TOOL_PYTHON=... python mcst_paper2.py eval --provider vllm --base-url ... --model local --dataset mathconstraint --output <dir>/tools.json ...
Temporary files: the authors' tool runs use TemporaryDirectory (removed by their code); wandb disabled."""
import json, sys
import math_constraint.eval as E

RAW = []


def robust(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            v = json.loads(raw)
            if isinstance(v, dict):
                return v
        except json.JSONDecodeError:
            pass
        RAW.append(raw[:300])
        try:
            v = json.loads(raw, strict=False)
            if isinstance(v, dict):
                return {**v, "_repaired": "strict=False"}
        except json.JSONDecodeError:
            pass
        if raw.strip():
            return {"code": raw, "_repaired": "raw-as-code"}
    return {}


E._parse_tool_arguments = robust

if __name__ == "__main__":
    from math_constraint.cli import main
    sys.argv = ["math_constraint"] + sys.argv[1:]
    try:
        rc = main()
    finally:
        out = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--output"), None)
        if out:
            json.dump({"n_unreadable": len(RAW), "examples": RAW[:50]}, open(out.replace(".json", "_unreadable_args.json"), "w"))
    raise SystemExit(rc)
