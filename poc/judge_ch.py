"""CH-P6 (docs/prereg/PREREG_CH.md): is the hint followed? An LLM judge (gpt-oss-120b, low effort) reads the hint and the program.
TAG: which of the given tags' techniques the program actually uses; PLAN: whether the program implements the plan's main approach.
Resumable, row by row. usage: CC_SET=full POC_BASE_URL=... POC_REASONING_EFFORT=low python judge_ch.py <model> [arm ...]
-> results/h2/ch_judge_<model>_<arm>_s<seed>.jsonl"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import RES  # noqa: E402
from llm import chat  # noqa: E402

TAG_Q = ("Below is a program written for a programming-contest problem, and a list of technique tags. For EACH tag, decide whether the "
         "program's algorithm actually uses that technique (not merely mentions it in a comment).\n\nTags: {tags}\n\nProgram:\n```python\n{code}\n```\n\n"
         "Answer with one line of JSON only, for example {{\"uses\": [\"binary search\"]}} (an empty list if it uses none of them).")
PLAN_Q = ("Below is a plan written before coding and the program written afterwards. Does the program implement the plan's MAIN approach "
          "(the same key idea and algorithm; small changes in details are fine)?\n\nPlan:\n{plan}\n\nProgram:\n```python\n{code}\n```\n\n"
          "Answer with one line of JSON only: {{\"follows\": true}} or {{\"follows\": false}}, plus a key \"why\" with at most 15 words.")


def parse(text):
    m = re.findall(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m[-1]) if m else None
    except ValueError:
        return None


if __name__ == "__main__":
    m = sys.argv[1]
    for arm in sys.argv[2:] or ["tag", "plan"]:
        for s in (1, 2, 3):
            src = f"{RES}/cc_full_{m}_medium_{arm}_s{s}.jsonl"
            if not os.path.exists(src):
                continue
            rows = [json.loads(l) for l in open(src) if l.strip()]
            path = f"{RES}/ch_judge_{m}_{arm}_s{s}.jsonl"
            done = {json.loads(l)["name"] for l in open(path)} if os.path.exists(path) else set()

            def one(r):
                q = (TAG_Q.format(tags=", ".join(r["tags"]), code=r["code"][:6000]) if arm == "tag"
                     else PLAN_Q.format(plan=(r.get("plan") or "")[:3000], code=r["code"][:6000]))
                o = chat(q, max_tokens=3000, temperature=0.0, seed=zlib.crc32(r["name"].encode()) % 997)
                j = parse(o["text"])
                out = {"name": r["name"], "seed": s, "arm": arm, "judge": j, "raw": (o["text"] or "")[-300:], "passed_all": r["passed_all"]}
                if arm == "tag":
                    out["tags"] = r["tags"]
                return out
            todo = [r for r in rows if r.get("code") and r["name"] not in done]
            with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
                for fu in as_completed([ex.submit(one, r) for r in todo]):
                    f.write(json.dumps(fu.result()) + "\n"); f.flush()
            print(m, arm, s, "judged", sum(1 for _ in open(path)), flush=True)
