"""HO-VR (docs/prereg/PREREG_HO.md, addendum): a short thinking-mode review of a cheap program as the escalation gate. For every library
program (formx) that passes the free check (runs, prints a value that is not 'No Best Solution'), the same Qwen3 model, in thinking mode cut
at B tokens (budget forcing), reads the problem, the program and its printed value and answers VERDICT: CORRECT or VERDICT: WRONG.
No labels. REVIEW_ANSWER_MAX (default 512) caps the answer after the thinking budget (HO-VR3: 2048 for Qwen3.5-9B, whose answers
are long). usage: NLOPT_SET=bwor POC_BASE_URL=... python run_review.py <model> <seed> [B=2000] [arm=formx]
-> results/x3/review_<model>_<set>_<arm>_s<seed>.jsonl (resumes; OptiBench: FORM_SUBSET=0/3 as HO-TF)
HO-VR2: NLOPT_SET=geo reviews the held-out geometry fact programs that pass the metamorphic check (results/geocross_S2_HOG_<m>_geo_fact)
-> results/x3/review_<model>_geo_fact_s<seed>.jsonl."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, _rows, problems  # noqa: E402

ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")
ASK = """{q}

A program was written for this problem:
```python
{code}
```
It printed the optimal objective value {pred}.

Do not solve the problem from scratch. Review the program against the problem text: are the decision variables (including integrality),
every constraint (direction and coefficients), the objective (direction and coefficients) and all numbers taken correctly from the text?
End with exactly one line: `VERDICT: CORRECT` if the program models the problem correctly, or `VERDICT: WRONG` otherwise."""
ASK_GEO = """{q}

A program was written for this problem (input on stdin in this format: {fmt}):
```python
{code}
```
On the given input it printed {pred}.

Do not solve the problem from scratch. Review the program against the statement: does it compute what is asked for every valid input,
including the special and degenerate cases the statement allows (for example collinear or repeated points, points exactly on a boundary,
shapes that only touch)? End with exactly one line: `VERDICT: CORRECT` if it is correct for all valid inputs, or `VERDICT: WRONG` otherwise."""


def main():
    from run_geo_cross import budget_chat
    m, seed = sys.argv[1], int(sys.argv[2])
    B = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    SET = os.environ.get("NLOPT_SET", "bwor")
    arm = sys.argv[4] if len(sys.argv) > 4 else "formx"
    if SET == "geo":
        return review_geo(m, seed, B)
    Q = {p["id"]: p for p in problems(SET)}
    F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{SET}_{arm}_s{seed}.jsonl")}
    if os.environ.get("FORM_SUBSET"):
        i0, k = map(int, os.environ["FORM_SUBSET"].split("/")); keep = {p["id"] for p in problems(SET)[i0::k]}
        F = {i: r for i, r in F.items() if i in keep}
    path = f"{RES}/review_{m}_{SET}_{arm}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    todo = [f for i, f in F.items() if i not in done and ok_(f) and f.get("code")]

    def one(f):
        o = budget_chat(ASK.format(q=Q[f["id"]]["q"], code=f["code"].strip(), pred=f["pred"]), B, max_tokens=int(os.environ.get("REVIEW_ANSWER_MAX", 512)), temperature=0.7,
                        seed=seed * 1000 + zlib.crc32(f["id"].encode()) % 997 + 41)
        v = re.findall(r"VERDICT:\s*(CORRECT|WRONG)", o["text"] or "")
        return {"id": f["id"], "verdict": v[-1] if v else None, "accept": bool(v and v[-1] == "CORRECT"), "out_tokens": o.get("out_tokens"),
                "think_tokens": o.get("think_tokens"), "text": (o["text"] or "")[-400:]}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as fh:
        for fu in as_completed([ex.submit(one, f) for f in todo]):
            fh.write(json.dumps(fu.result()) + "\n"); fh.flush()
    R = _rows(path)
    print(m, SET, seed, f"reviewed {len(R)}: accept {sum(r['accept'] for r in R)}, wrong {sum(r['verdict'] == 'WRONG' for r in R)}, "
          f"no verdict {sum(r['verdict'] is None for r in R)}", flush=True)


def review_geo(m, seed, B):
    import random
    from run_geo_cross import budget_chat
    import analyze_n10 as N
    from analyze_hogc import load, outs
    from run_geo import base_instance, render, variants
    F = load(f"S2_HOG_{m}_geo_fact_s{seed}")
    path = f"{RES}/review_{m}_geo_fact_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    todo = [(k, f) for k, f in F.items() if "|".join(map(str, k)) not in done and f.get("code") and N.geo_check(f)[0]]

    def one(kf):
        k, f = kf
        rng = random.Random(f"{f['task']}-{f['n']}-{f['inst']}")
        q, _, fmt = render(f["task"], variants(f["task"], base_instance(f["task"], f["n"], rng), rng)["identity"])
        o = budget_chat(ASK_GEO.format(q=q, fmt=fmt, code=f["code"].strip(), pred=(outs(f) or ["?"])[0]), B, max_tokens=int(os.environ.get("REVIEW_ANSWER_MAX", 512)), temperature=0.7,
                        seed=seed * 1000 + zlib.crc32("|".join(map(str, k)).encode()) % 997 + 43)
        v = re.findall(r"VERDICT:\s*(CORRECT|WRONG)", o["text"] or "")
        return {"id": "|".join(map(str, k)), "verdict": v[-1] if v else None, "accept": bool(v and v[-1] == "CORRECT"),
                "out_tokens": o.get("out_tokens"), "think_tokens": o.get("think_tokens"), "text": (o["text"] or "")[-400:]}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as fh:
        for fu in as_completed([ex.submit(one, kf) for kf in todo]):
            fh.write(json.dumps(fu.result()) + "\n"); fh.flush()
    R = _rows(path)
    print(m, "geo", seed, f"reviewed {len(R)}: accept {sum(r['accept'] for r in R)}", flush=True)


if __name__ == "__main__":
    main()
