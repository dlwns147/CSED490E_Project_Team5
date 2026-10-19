"""STORM baseline (docs/prereg/PREREG_X7.md): write our problem sets (full MAMO 863; NL4OPT + IndustryOR 345) in STORM's official
tool-integrated-reasoning prompt format, for its own inference code (github.com/tangzhy/STORM, cloned to /SSD/lean_postech/storm/STORM)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import problems  # noqa: E402

D = "/SSD/lean_postech/storm/STORM/data"
prefix = json.loads(open(f"{D}/test.tir_prompt.mamo_easy.jsonl").readline())["prompt"].split("### Problem:\n")[0] + "### Problem:\n"
for name, which in (("mamo_full", "mamo"), ("x3", "x3")):
    with open(f"{D}/test.tir_prompt.{name}.jsonl", "w") as f:
        for p in problems(which):
            f.write(json.dumps({"prompt": prefix + p["q"], "gt_answer": p["gold"], "data_source": p["src"], "id": p["id"]}) + "\n")
    print(name, len(problems(which)))
