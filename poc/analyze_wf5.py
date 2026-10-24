"""WF5 (docs/prereg/PREREG_HO.md, addendum): the census rule's "do not add a fact" side on the fine-tuned models. Per cell: the free
program, + usage card (freef), + label-free library (formx), 3 seeds; gain = with fact - free with a paired 95% interval over problems,
output tokens, and the fact's extra input tokens (Qwen3 tokenizer; the library: the shown program for each problem, as run_form builds it).
usage: POC_DATA=... python analyze_wf5.py"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import RES, _rows, problems  # noqa: E402

# (tag, set, call recorded before any gain was read, facts run prospectively)
CELLS = [("q14sft", "optibench", "add", ("freef", "formx")), ("q14sft", "bwor", "do not add", ("freef", "formx")),
         ("q14sft", "logior", "add", ("freef", "formx")), ("q14sft", "optmath", "add", ("formx",)),
         ("q8bsft2", "bwor", "do not add", ("freef", "formx")), ("q8bsft", "bwor", "do not add", ("freef",)),
         ("q8bsft", "optmath", "add", ("formx",))]
RETRO = [("q8bsft", "bwor", "do not add", ("formx",))]   # read in DT2 before the rule was applied here: reported, not counted


def tokenizer():
    from tokenizers import Tokenizer
    return Tokenizer.from_file(os.path.join(os.environ["POC_DATA"], "stage", "Qwen3-14B-AWQ", "tokenizer.json"))


def extra_input(bench, fact, tk):
    """mean extra prompt tokens of the fact over the set's problems"""
    if fact == "freef":
        from run_nlopt import LIBCARD
        return len(tk.encode(LIBCARD).ids)
    os.environ["NLOPT_SET"] = bench
    import importlib
    import run_form
    importlib.reload(run_form)   # its SET is read at import
    sel = run_form.selector()
    n = [len(tk.encode(s[1][1]).ids) + 30 if (s := sel(p)) else 0 for p in problems(bench)]
    return sum(n) / len(n)


def cell(tag, bench, fact):
    F = {s: {r["id"]: r for r in _rows(f"{RES}/opt_{tag}_{bench}_free_s{s}.jsonl")} for s in (1, 2, 3)}
    X = {s: {r["id"]: r for r in _rows(f"{RES}/opt_{tag}_{bench}_{fact}_s{s}.jsonl")} for s in (1, 2, 3)}
    ids = [i for i in F[1] if all(i in F[s] and i in X[s] for s in (1, 2, 3))]
    if len(ids) < len(F[1]):
        return None
    acc = lambda D: 100 * sum(D[s][i]["correct"] for s in (1, 2, 3) for i in ids) / (3 * len(ids))
    tok = lambda D: sum(D[s][i]["out_tokens"] or 0 for s in (1, 2, 3) for i in ids) / (3 * len(ids))
    d = ci({i: sum(X[s][i]["correct"] - F[s][i]["correct"] for s in (1, 2, 3)) / 3 for i in ids})
    return len(ids), acc(F), tok(F), acc(X), tok(X), d


def main():
    tk = tokenizer(); right = []
    for group, cells in (("prospective", CELLS), ("retrospective (not counted)", RETRO)):
        print(f"== {group}")
        for tag, bench, call, facts in cells:
            for fact in facts:
                r = cell(tag, bench, fact)
                if r is None:
                    print(f"  {tag:8s} {bench:9s} {fact}: incomplete"); continue
                n, a0, t0, a1, t1, (mu, lo, hi) = r
                ok = (mu <= 2) if call == "do not add" else (mu >= 2)
                if group == "prospective":
                    right.append((call, ok))
                print(f"  {tag:8s} {bench:9s} call {call:10s} {fact}: free {a0:.1f}% @ {t0:.0f} -> {a1:.1f}% @ {t1:.0f} | gain {mu:+.1f} "
                      f"[{lo:+.1f}, {hi:+.1f}] {'right' if ok else 'WRONG'} | extra input {extra_input(bench, fact, tk):.0f} tokens (n={n})")
    for c in ("do not add", "add"):
        k = [ok for cc, ok in right if cc == c]
        print(f"{c}: {sum(k)} / {len(k)} calls right")


if __name__ == "__main__":
    main()
