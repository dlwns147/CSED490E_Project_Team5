"""ORLM baseline (docs/prereg/PREREG_X7.md, addendum): ORLM-LLaMA-3-8B (Tang et al., ORLM, fine-tuned for optimization modeling) on the same
word problems and grader as X3 / X6 / X7. Its own completion template (no chat template) and solver (coptpy). The objective is read from the
solver itself: Model.solve is wrapped to record (status, objval), printed at exit; status 1 = optimal, infeasible / unbounded = 'No Best Solution'.
usage: [NLOPT_SET=mamo] POC_BASE_URL=... python run_orlm.py <tag> <seed> [--max_tokens N]   (seed 1 = greedy, as on the model card; 2-3 sampled T 0.7)
       -> results/x3/opt_<tag>_orlm_s<seed>.jsonl"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, problems, correct, _rows  # noqa: E402
from sandbox import run_python  # noqa: E402

TEMPLATE = ("Below is an operations research question. Build a mathematical model and corresponding python code using `coptpy` that "
            "appropriately addresses the question.\n\n# Question:\n{q}\n\n# Response:\n")
PRELUDE = '''import coptpy as _cp, atexit as _ax
_orig_solve = _cp.Model.solve
_last = [None]
def _solve(self, *a, **k):
    r = _orig_solve(self, *a, **k)
    try:
        _last[0] = (self.status, self.objval if self.status == 1 else None)
    except Exception:
        _last[0] = (getattr(self, "status", None), None)
    return r
_cp.Model.solve = _solve
_ax.register(lambda: print("__OBJ__", _last[0]))
'''


def code_of(text):
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text or "", re.S)
    return blocks[-1] if blocks else None


def pred_of(stdout):
    m = re.findall(r"__OBJ__ \((-?\d+), (.*?)\)", stdout or "")
    if not m:
        return None
    st, val = int(m[-1][0]), m[-1][1].strip()
    if st == 1 and val not in ("None", ""):
        return float(val)
    return "NBS" if st in (2, 3, 4) else None   # COPT: 2 infeasible, 3 unbounded, 4 infeasible or unbounded


if __name__ == "__main__":
    from openai import OpenAI
    tag, seed = sys.argv[1], int(sys.argv[2])
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 4096
    client = OpenAI(base_url=os.environ["POC_BASE_URL"], api_key="none", timeout=3600)
    path = f"{RES}/opt_{tag}_orlm_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}

    def one(p):
        r = client.completions.create(model="local", prompt=TEMPLATE.format(q=p["q"]), max_tokens=mt,
                                      temperature=0.0 if seed == 1 else 0.7, seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        text = r.choices[0].text or ""
        code = code_of(text)
        res = run_python(PRELUDE + code, "", timeout=60, mem_bytes=4 << 30) if code else None
        pred = pred_of(res.stdout) if res else None
        return {"id": p["id"], "src": p["src"], "gold": p["gold"], "mode": "orlm", "out_tokens": r.usage.completion_tokens,
                "finish": r.choices[0].finish_reason, "code": code, "status": (res.status if res else "no_code"),
                "stdout": (res.stdout if res else "")[-300:], "err": ((res.stderr or "")[-300:] if res else ""), "pred": pred,
                "correct": correct(pred, p["gold"])}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in problems() if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = _rows(path); by = {}
    for r in rows:
        by.setdefault(r["src"], []).append(r["correct"])
    print(tag, seed, {k: f"{sum(v)}/{len(v)}" for k, v in by.items()}, f"tokens {sum(r['out_tokens'] or 0 for r in rows) / max(1, len(rows)):.0f}", flush=True)
