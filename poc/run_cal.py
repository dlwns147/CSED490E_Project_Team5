"""NaturalPlan Calendar Scheduling, headroom pilot (exploratory, 11-14): how far is thinking from the ceiling on Amonkar et al.'s 100 calendar
items, and at what token cost, before any translation arm is built. A second planning domain for the count gate only pays if thinking leaves
room or spends many tokens.

usage: run_cal.py <tag> <arm think|direct> <seed>   writes results/cal_<tag>_<arm>_s<seed>.jsonl (id, exact, slot, gold, tokens, finish, text tail)
Data: nlp_data/naturalplan_dl/a_calendar_scheduling_100.json (Amonkar et al.'s 100, NaturalPlan's 5-shot prompt as is).
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f"{ROOT}/results"
FMT = "{p}\n\nSolve the task. On the last line give the meeting as: Day, HH:MM - HH:MM"
SLOT = re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday)\W+(\d{1,2}):(\d{2})\s*(?:-|–|to)\s*(\d{1,2}):(\d{2})")


def slot(text):
    """the last 'Day, HH:MM - HH:MM' in the text, as (day, start minute, end minute), or None"""
    m = SLOT.findall(text or "")
    if not m:
        return None
    d, h1, m1, h2, m2 = m[-1]
    return (d, int(h1) * 60 + int(m1), int(h2) * 60 + int(m2))


def main():
    tag, arm, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    D = json.load(open(os.path.join(os.environ["POC_DATA"], "naturalplan_dl", "a_calendar_scheduling_100.json")))

    def run(item):
        i, r = item
        p = r["prompt_5shot"].rstrip()
        p = re.sub(r"\s*SOLUTION:\s*$", "", p)
        o = chat_msgs([{"role": "user", "content": FMT.format(p=p)}], think=arm == "think", max_tokens=int(os.environ.get("CAL_MAXTOK", 32000)) if arm == "think" else 4096,
                      temperature=0.7, seed=seed * 10007 + int(i.rsplit("_", 1)[1]))
        s, g = slot(o["text"]), slot(r["golden_plan"])
        return {"id": i, "arm": arm, "seed": seed, "people": r["num_people"], "days": r["num_days"], "exact": s is not None and s == g,
                "slot": s, "gold": g, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-800:]}

    path = f"{RES}/cal_{tag}_{arm}_s{seed}.jsonl"
    rows = []
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        for row in ex.map(run, sorted(D.items())):
            rows.append(row); f.write(json.dumps(row) + "\n"); f.flush()
    print(tag, arm, seed, f"{sum(r['exact'] for r in rows)}/{len(rows)}", f"tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}", flush=True)


if __name__ == "__main__":
    main()
