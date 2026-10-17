"""B3 (docs/prereg/PREREG_B3.md): one-round DRAFT-style documentation rewriting (2410.08197) of the needed `in_circle` helper.
The model sees the helper with its terse comment, writes up to 6 probe calls (a Python snippet that prints results), we execute them with the
helper defined, show the printed output, and the model rewrites the helper's one-line comment so that it documents the behaviour, including
any precondition. R independent rewrites per model (seeds 1..R) -> results/draft_docs_<tag>.json
usage: POC_BASE_URL=... python draft_doc.py <tag> [R=3]"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import INCIRCLE_VARIANTS  # noqa: E402
from llm import chat_msgs, last_block, strip_think  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
tag = sys.argv[1]; R = int(sys.argv[2]) if len(sys.argv) > 2 else 3
HELPER = INCIRCLE_VARIANTS["signed"]
out = []
for sd in range(1, R + 1):
    msgs = [{"role": "user", "content": "Here is a helper function from a library:\n```python\n" + HELPER + "```\nBefore we document it properly, "
             "explore its behaviour. Write a short Python snippet (at most 6 calls) that calls `in_circle` on inputs of your choice and prints "
             "each input and result; the function is already defined. Give the snippet in a single ```python code block."}]
    o1 = chat_msgs(msgs, think=False, max_tokens=1500, temperature=0.7, seed=sd)
    probe = last_block(o1["text"], ("python", "py", "python3")) or ""
    r = run_python(HELPER + "\n" + probe, "", timeout=10)
    shown = (r.stdout[-2500:] if r.status == "ok" else f"(error) {r.stderr[-800:]}")
    msgs += [{"role": "assistant", "content": strip_think(o1["text"])},
             {"role": "user", "content": f"Output of your snippet:\n```\n{shown}\n```\nNow rewrite the one-line comment of `in_circle` so that a "
              "programmer who reads only the comment uses the function correctly (state what the sign of the result means and any precondition "
              "on the arguments). Reply with the new comment only, on one line, starting with #."}]
    o2 = chat_msgs(msgs, think=False, max_tokens=300, temperature=0.7, seed=100 + sd)
    lines = [l.strip() for l in strip_think(o2["text"]).splitlines() if l.strip().startswith("#")]
    doc = (lines[0] if lines else strip_think(o2["text"]).strip().splitlines()[0]).lstrip("#").strip()
    out.append({"seed": sd, "probe": probe, "probe_output": shown, "doc": doc, "tokens": o1["out_tokens"] + o2["out_tokens"],
                "mentions_orientation": bool(re.search(r"counter|clockwise|orient|ccw", doc, re.I))})
    print(sd, out[-1]["tokens"], "tok |", doc)
json.dump(out, open(f"{RES}/draft_docs_{tag}.json", "w"), indent=1)
