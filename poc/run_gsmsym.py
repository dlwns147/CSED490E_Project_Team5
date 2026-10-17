"""X2 (results/PREREG_X2.md): verify once, reuse on math word problems with numeric variants (GSM-Symbolic, 100 templates).
Per template: instances 0-19 (instance 0 = the one shown to the model; 1-3 = the labelled check; 4-19 = held-out).
  text   : per-instance text answer (\\boxed{}), all 20 instances.
  solver : 4 candidate programs (seeds 1-4) `solve(question: str) -> number` written from instance 0, meant for any variant (names,
           objects and numbers change); the first candidate right on instances 1-3 (else the one right on most) is reused unchanged
           on instances 4-19.
usage: POC_BASE_URL=... python run_gsmsym.py <tag> text|solver   -> results/x2/gsm_<tag>_<mode>.jsonl ; python run_gsmsym.py --grade <tag>"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OUT = f"{RES}/x2"
NI = 20


def data():
    R = json.load(open(f"{RES}/math/gsmsym.json"))
    T = {}
    for r in R:
        if int(r["instance"]) < NI:
            gold = float(r["answer"].split("####")[-1].strip().replace(",", ""))
            T.setdefault(r["original_id"], {})[int(r["instance"])] = {"q": r["question"], "gold": gold}
    return T


TEXT = "{q}\n\nSolve the problem. Put the final numeric answer in \\boxed{{}}."
SOLVER = ("Here is a math word problem:\n\n{q}\n\nWrite a Python function `solve(question: str) -> float` that returns the numeric answer for "
          "this problem AND for any variant of it in which the names, objects and numbers change but the wording and structure stay the "
          "same. The function must read every number it needs from the `question` text itself (do not hard-code the numbers above). "
          "Use only the Python standard library. Give only the function (and helper code it needs) in a single ```python code block.")
HARNESS = "\n\nimport sys, json\nqs = json.loads(sys.stdin.read())\nout = []\nfor q in qs:\n    try:\n        out.append(float(solve(q)))\n    except Exception as e:\n        out.append(None)\nprint(json.dumps(out))\n"


def num_close(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b))


def boxed_num(text):
    m = re.findall(r"\\boxed\{([^{}]*)\}", text or "")
    if not m:
        return None
    s = m[-1].replace(",", "").replace("$", "").replace("\\%", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        try:
            from fractions import Fraction
            return float(Fraction(s))
        except Exception:
            return None


def main(tag, mode):
    from llm import chat, last_block
    from sandbox import run_python
    T = data(); os.makedirs(OUT, exist_ok=True)
    rows = []
    if mode == "text":
        jobs = [(t, i) for t in T for i in range(NI)]
        def one(j):
            t, i = j; it = T[t][i]
            o = chat(TEXT.format(q=it["q"]), temperature=0.7, max_tokens=4096, seed=1000 + zlib.crc32(f"{t}-{i}".encode()) % 997)
            a = boxed_num(o["text"])
            return {"template": t, "instance": i, "gold": it["gold"], "pred": a, "correct": num_close(a, it["gold"]),
                    "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), "text": (o["text"] or "")[-800:]}
        with ThreadPoolExecutor(48) as ex:
            rows = list(ex.map(one, jobs))
    else:
        jobs = [(t, k) for t in T for k in (1, 2, 3, 4)]
        def one(j):
            t, k = j
            o = chat(SOLVER.format(q=T[t][0]["q"]), temperature=0.7, max_tokens=4096, seed=k * 1000 + zlib.crc32(str(t).encode()) % 997)   # template ids are ints (fixed 19:06: solver runs crashed)
            code = last_block(o["text"] or "", ("python", "py", "python3"))
            preds = [None] * NI
            if code:
                r = run_python(code + HARNESS, json.dumps([T[t][i]["q"] for i in range(NI)]), timeout=30)
                try:
                    preds = json.loads(r.stdout.strip().splitlines()[-1]) if r.status == "ok" else preds
                except Exception:
                    pass
            ok = [num_close(preds[i], T[t][i]["gold"]) for i in range(NI)]
            return {"template": t, "cand": k, "code": code, "preds": preds, "ok": ok, "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        with ThreadPoolExecutor(48) as ex:
            rows = list(ex.map(one, jobs))
    with open(f"{OUT}/gsm_{tag}_{mode}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(tag, mode, "done", len(rows), flush=True)


def grade(tag):
    T = [json.loads(l) for l in open(f"{OUT}/gsm_{tag}_text.jsonl")]
    S = [json.loads(l) for l in open(f"{OUT}/gsm_{tag}_solver.jsonl")]
    held = range(4, NI)
    txt = [r for r in T if r["instance"] in held]
    by = {}
    for r in S:
        by.setdefault(r["template"], []).append(r)
    ok = n = tok = picked_none = 0
    for t, C in by.items():
        C.sort(key=lambda r: r["cand"])
        good = [c for c in C if all(c["ok"][1:4])]
        pick = good[0] if good else max(C, key=lambda c: sum(c["ok"][1:4]))
        picked_none += not good
        ok += sum(pick["ok"][i] for i in held); n += len(held); tok += sum(c["out_tokens"] or 0 for c in C)
    print(f"{tag}: per-instance text on held-out {100 * sum(r['correct'] for r in txt) / len(txt):.1f}% @ "
          f"{sum(r['out_tokens'] or 0 for r in txt) / len(txt):.0f} tokens per instance | verify-once-reuse {100 * ok / n:.1f}% @ "
          f"{tok / (len(by) * NI):.0f} tokens per instance (4 candidates per template, amortised over {NI} instances); templates with no "
          f"candidate right on the 3 checks: {picked_none} / {len(by)}; candidate programs right on all 20: "
          f"{sum(all(c['ok']) for C in by.values() for c in C)} / {sum(len(C) for C in by.values())}")


if __name__ == "__main__":
    if sys.argv[1] == "--grade":
        grade(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
