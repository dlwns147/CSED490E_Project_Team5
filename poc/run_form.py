"""FORM (docs/prereg/PREREG_X7.md, 2026-10-19): systematic formulation errors on recurring MAMO problem types (a TSP written with
Miller-Tucker-Zemlin order constraints that include the start city; a supply redistribution written as an equality, so surplus cannot stay)
are not fixed by a repair turn or by thinking. Are they missing knowledge that one fact fixes?
modes: formh = the mips prompt (automatic API example) + ONE hand-written formulation sentence, only for the two problem types (mechanism test);
       formx = label-free: P_MIP + a program for the most similar OTHER MAMO problem (BM25), taken from a pool of all five models' programs
               that pass the strict check (two seeds run, agree, and are not 'No Best Solution'); among that problem's programs the one
               whose answer most other models share, then the shortest. No labels anywhere.
       forms = formx with the pool restricted to the SAME model's own programs (control: self-improvement, no other model).
usage: NLOPT_SET=mamo POC_BASE_URL=... python run_form.py <model> <mode> <seed>   -> results/x3/opt_<model>_mamo_<mode>_s<seed>.jsonl"""
import json, math, os, re, sys, zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, P_MIP, problems, value_of, correct, _rows, _verified_examples  # noqa: E402

POOL_MODELS = ("oss20", "q14a", "q8b", "q32b", "q36")
FACT = {"tsp": "Formulation note: with Miller-Tucker-Zemlin subtour elimination, write the order constraints u[i] - u[j] + n*x[i][j] <= n - 1 "
               "only for cities i, j other than the start city, with 1 <= u[i] <= n - 1; constraining the start city too makes the model infeasible.",
        "redistribution": "Formulation note: a center may end with more supplies than it needs; require final stock >= need (not == need), "
                          "otherwise any total surplus makes the model infeasible."}


def kind(q):   # problem type, used only to place the hand-written sentence (formh) and to report results by type
    q = q.lower()
    if "each city exactly once" in q or "salesperson" in q:
        return "tsp"
    if re.search(r"has \d+ units but needs", q) or "redistribut" in q:
        return "redistribution"
    return None


def same(a, b):
    if a is None or b is None:
        return False
    if "NBS" in (a, b):
        return a == b
    return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))


def pool(models=POOL_MODELS):
    """problem id -> list of (model, code, answer, n_models_sharing_the_answer) over strict-check-passing programs"""
    by = {}
    for m in models:
        A, B = ({r["id"]: r for r in _rows(f"{RES}/opt_{m}_mamo_mips_s{s}.jsonl")} for s in (1, 2))
        for i, a in A.items():
            b = B.get(i)
            if b and a.get("status") == "ok" and b.get("status") == "ok" and a.get("pred") not in (None, "NBS") and same(a["pred"], b["pred"]) and a.get("code"):
                by.setdefault(i, []).append((m, a["code"], a["pred"]))
    return {i: [(m, c, v, len({m2 for m2, _, v2 in L if same(v, v2)})) for m, c, v in L] for i, L in by.items()}


def selector(models=POOL_MODELS):
    Q = {p["id"]: p for p in problems()}
    PL = pool(models)
    tok = lambda t: re.findall(r"[a-z]+", t.lower())
    docs = {i: Counter(tok(Q[i]["q"])) for i in PL if i in Q}
    df = Counter(w for d in docs.values() for w in d); N = max(1, len(docs)); avg = sum(sum(d.values()) for d in docs.values()) / N

    def best(p):
        q = set(tok(p["q"]))
        sc = [(sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * d[w] * 2.2 / (d[w] + 1.2 * (.25 + .75 * sum(d.values()) / avg)) for w in q if w in d), i)
              for i, d in docs.items() if i != p["id"]]   # leave-one-out: never the problem itself
        if not sc:
            return None
        i = max(sc)[1]
        return i, max(PL[i], key=lambda e: (e[3], -len(e[1])))
    return best


if __name__ == "__main__":
    from llm import chat, last_block
    from sandbox import run_python
    m, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    tag = f"{m}_mamo"
    os.environ["NLOPT_EX_SHORTEST"] = "1"
    EX = _verified_examples(os.environ.get("NLOPT_EX_TAG", m))   # the mips example, kept in formh so only the sentence differs
    SEL = selector() if mode == "formx" else selector((m,)) if mode == "forms" else None
    P = [p for p in problems() if mode != "formh" or kind(p["q"])]
    path = f"{RES}/opt_{tag}_{mode}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}

    def one(p):
        q = P_MIP.format(q=p["q"]); src = None
        if mode == "formh":
            ex = EX(p)
            if ex:
                q += "\n\nA program that runs with this library (written for a different problem):\n```python\n" + ex.strip() + "\n```"
            q += "\n\n" + FACT[kind(p["q"])]
        else:
            s = SEL(p)
            if s:
                src = (s[0], s[1][0], s[1][3])
                q += ("\n\nA program for a similar problem (two independent runs of it agree and its model is feasible):\n```python\n"
                      + s[1][1].strip() + "\n```")
        o = chat(q, max_tokens=8192, temperature=0.7, seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        res = run_python(code, "", timeout=60, mem_bytes=4 << 30) if code else None
        out = (res.stdout if res and res.status == "ok" else "") or ""
        lines = [l for l in out.strip().splitlines() if l.strip()]
        pred = value_of(lines[-1]) if lines else None
        return {"id": p["id"], "src": p["src"], "kind": kind(p["q"]), "gold": p["gold"], "mode": mode, "out_tokens": o.get("out_tokens"),
                "finish": o.get("finish"), "code": code, "status": (res.status if res else "no_code"), "stdout": out[-300:],
                "err": ((res.stderr or "")[-300:] if res else ""), "pred": pred, "correct": correct(pred, p["gold"]), "fact_from": src}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = _rows(path); by = {}
    for r in rows:
        by.setdefault(r["kind"] or "other", []).append(r["correct"])
    print(tag, mode, seed, {k: f"{sum(v)}/{len(v)}" for k, v in by.items()}, f"tokens {sum(r['out_tokens'] or 0 for r in rows) / max(1, len(rows)):.0f}", flush=True)
