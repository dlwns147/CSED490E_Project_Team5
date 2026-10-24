"""DT (docs/prereg/PREREG_DT.md): label-free fine-tuning data from the recipe's strict check. Development sets only (NL4OPT + IndustryOR,
MAMO). For each problem, the programs of the stored cheap runs that pass the strict check (seed 1 and seed 2 both run, print a value that is
not 'No Best Solution', and agree); keep the one whose answer most models share, then the shortest (as run_form.pool). No label is read.
Prompt = the solver-choice prompt P_FREE (no fact); target = the program in a Python block.
DT3: `--round2` also takes the unlabeled problems (poc/build_unlabeled.py) that the round-1 model solved twice in agreement
-> checked_programs_r2.jsonl. DT4: `--round2 --cross` keeps an unlabeled problem only if gpt-oss-20b's value (oss20_unlabeled free s1)
agrees too -> checked_programs_r2x.jsonl.
usage: python build_sft_data.py [--round2]  -> $POC_DATA/sft/checked_programs.jsonl"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import DATA, P_FREE, RES, _rows, problems  # noqa: E402

SOURCES = {"x3": ("{m}_mipf", ("q17", "q4b", "q8b", "q14a", "oss20", "q32b", "q36")),
           "mamo": ("{m}_mamo_mips", ("oss20", "q14a", "q8b", "q32b", "q36"))}
if "--round2" in sys.argv:
    SOURCES["unlabeled"] = ("{m}_unlabeled_free", ("q8bsft",))
CROSS = {r["id"]: r for r in _rows(f"{RES}/opt_oss20_unlabeled_free_s1.jsonl")} if "--cross" in sys.argv else None


def same(a, b):
    return a is not None and b is not None and a != "NBS" and b != "NBS" and abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))


def main():
    out = []
    for which, (src, models) in SOURCES.items():
        Q = {p["id"]: p for p in problems(which)}
        by = {}
        for m in models:
            A, B = ({r["id"]: r for r in _rows(f"{RES}/opt_{src.format(m=m)}_s{s}.jsonl")} for s in (1, 2))
            for i, a in A.items():
                b = B.get(i)
                if b and a.get("status") == "ok" and b.get("status") == "ok" and same(a.get("pred"), b.get("pred")) and a.get("code"):
                    by.setdefault(i, []).append((m, a["code"], a["pred"]))
        for i, L in by.items():
            if i not in Q:
                continue
            if which == "unlabeled" and CROSS is not None:   # DT4: a different model must agree with the kept value
                c = CROSS.get(i)
                L = [e for e in L if c and c.get("status") == "ok" and same(e[2], c.get("pred"))]
                if not L:
                    continue
            m, code, v = max(L, key=lambda e: (len({m2 for m2, _, v2 in L if same(e[2], v2)}), -len(e[1])))
            out.append({"id": i, "set": which, "from": m, "prompt": P_FREE.format(q=Q[i]["q"]), "target": "```python\n" + code.strip() + "\n```"})
        print(which, f"{len(Q)} problems, {sum(1 for o in out if o['set'] == which)} with a strict-check-passing program", flush=True)
    os.makedirs(f"{DATA}/sft", exist_ok=True)
    with open(f"{DATA}/sft/checked_programs{'_r2' if '--round2' in sys.argv else ''}{'x' if '--cross' in sys.argv else ''}.jsonl", "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    print("wrote", len(out))


if __name__ == "__main__":
    main()
