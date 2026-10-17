"""N2 (docs/prereg/PREREG_N.md): one round of label-free feedback repair on the contest-geometry set.
A program that passes the statement's public examples is kept. Otherwise the model gets the statement, its program and the first failing
example (input, expected output, its output or the error / time-out, or "no program" if the reply had none) and writes a corrected
program, which is scored on all kept tests. Same model and mode as the source run.
usage: CC_SET=full POC_BASE_URL=... [POC_REASONING_EFFORT=low] python repair_cc.py <src_tag> <seed> [--think_budget B] [--max_tokens N]
       -> results/h2/cc_full_rep_<src_tag>_s<seed>.jsonl"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import OPRE, PFILE, RES, VFILE, tests_of, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

CUT = 1500


def clip(s):
    s = s or ""
    return s if len(s) <= CUT else s[:CUT] + f"\n... ({len(s) - CUT} more characters)"


def feedback(p, code, tol):
    """None if the program passes every public example, else the message for the first failing one."""
    if not code:
        return "Your previous reply did not contain a complete program in a ```python code block."
    for t in [t for t in p["tests"] if t["kind"] == "public"]:
        r = run_python(code, t["input"], timeout=10)
        if r.status == "tle":
            why = "It exceeded the time limit (10 seconds) on this input."
        elif r.status != "ok":
            why = "It crashed on this input:\n" + clip("\n".join((r.stderr or "").strip().split("\n")[-15:]))
        elif not tok_eq(r.stdout, t["output"], tol):
            why = "It printed:\n" + clip(r.stdout)
        else:
            continue
        return (f"Your program fails the example from the statement.\nInput:\n{clip(t['input'])}\nExpected output:\n{clip(t['output'])}\n{why}")
    return None


def main(src, seed, mode):
    from llm import chat, last_block
    import zlib
    P = {p["name"]: p for p in json.load(open(PFILE))}
    keep = json.load(open(VFILE))
    rows = {r["name"]: r for r in map(json.loads, open(f"{RES}/{OPRE}{src}_s{seed}.jsonl"))}

    def one(name):
        p, r = P[name], rows[name]; tol = keep[name]["tol"]
        fb = feedback(p, r["code"], tol)
        base = {"name": name, "rating": p["rating"], "orig_passed_all": r["passed_all"], "orig_tokens": r.get("out_tokens") or 0}
        if fb is None:
            return {**base, "repaired": False, "passed_all": r["passed_all"], "repair_tokens": 0, "code": r["code"]}
        prompt = (p["description"].strip() + "\n\nWrite a Python 3 program that reads the input from stdin and prints the answer to stdout. "
                  + (f"\n\nYour previous program:\n```python\n{r['code']}\n```\n" if r["code"] else "\n")
                  + "\n" + fb + "\n\nFind the mistake and fix it. Give the complete corrected program in a single ```python code block.")
        sd = 7000 + seed * 1000 + zlib.crc32(name.encode()) % 997
        if mode.get("think_budget"):
            from run_geo_cross import budget_chat
            o = budget_chat(prompt, mode["think_budget"], max_tokens=6000, temperature=0.7, seed=sd)
        else:
            o = chat(prompt, max_tokens=mode.get("max_tokens", 6000), temperature=0.7, seed=sd)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        T = tests_of(p); passed = 0
        if code:
            for t in T:
                x = run_python(code, t["input"], timeout=10)
                if x.status != "ok" or not tok_eq(x.stdout, t["output"], tol):
                    break
                passed += 1
        return {**base, "repaired": True, "passed_all": bool(code) and passed == len(T), "passed": passed, "repair_tokens": o.get("out_tokens") or 0,
                "finish": o.get("finish"), "feedback_kind": ("no code" if not r["code"] else "crash" if "crashed" in fb else
                                                         "timeout" if "time limit" in fb else "wrong"), "code": code,
                "text": (o.get("text") or "")[-3000:]}

    with ThreadPoolExecutor(16) as ex:
        out = list(ex.map(one, sorted(rows)))
    with open(f"{RES}/{OPRE}rep_{src}_s{seed}{os.environ.get('REP_SUFFIX', '')}.jsonl", "w") as f:   # N9: REP_SUFFIX=_med
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(src, seed, f"original {sum(r['orig_passed_all'] for r in out)} -> after one repair round {sum(r['passed_all'] for r in out)} of {len(out)};"
          f" repaired {sum(r['repaired'] for r in out)}; repair tokens per problem {sum(r['repair_tokens'] for r in out) / len(out):.0f}")


if __name__ == "__main__":
    mode = {}
    if "--think_budget" in sys.argv:
        mode["think_budget"] = int(sys.argv[sys.argv.index("--think_budget") + 1])
    if "--max_tokens" in sys.argv:
        mode["max_tokens"] = int(sys.argv[sys.argv.index("--max_tokens") + 1])
    main(sys.argv[1], int(sys.argv[2]), mode)
