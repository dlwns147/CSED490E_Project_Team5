"""PREREG_DIFF addendum PE (2026-11-23): resolve disagreeing Project Euler programs by a small case where they differ.
build : for every progc program (Qwen3-8B, gpt-oss-20b, gpt-oss-120b; seeds 1-3) whose solve() takes ONE argument, run solve(n) for
        n = 1..12 in the sandbox (5 s each, 45 s total) -> results/x44/pe_diff_sweep_<set>.jsonl
run   : per problem whose candidates' final answers disagree, take the smallest n where the swept classes' solve(n) differ and ask the
        oracle model for the problem's quantity at that size (the statement, the argument's name and the asked value are shown);
        keep the classes that match; up to 3 rounds; return the most frequent surviving final answer -> pe_diff_<set><tag>.jsonl
score : DIFF vs the plurality final answer and the best single source, accuracy and utility at 0.5 per ktok
usage: python pe_diff.py build <euler|eulert> | run <set> | score"""
import json, os, re, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute")
SRC = [("q8b", "q8bL"), ("oss20", "oss20"), ("oss120", "oss120")]
SWEEP = """

import signal as _s, time as _t
class _TO(Exception):
    pass
def _h(*_):
    raise _TO()
_s.signal(_s.SIGALRM, _h)
_t0 = _t.time()
for _n in range(1, 13):
    if _t.time() - _t0 > 45:
        break
    _s.setitimer(_s.ITIMER_REAL, 5.0)
    try:
        _v = repr(solve(_n))
    except _TO:
        _v = 'TIMEOUT'
    except Exception as e:
        _v = 'error'
    finally:
        _s.setitimer(_s.ITIMER_REAL, 0)
    print('__SW__', _n, _v, flush=True)
    if _v == 'TIMEOUT':
        break
"""
ASK = ("{p}\n\nA program for this problem defines solve({arg}) and the problem asks about {call}. Consider the SAME problem with {arg} = {n} "
       "instead (a small case). Compute the answer for that small case carefully from the problem's definitions. Give only the final "
       "integer in \\boxed{{}}.")


def norm(s):
    return re.sub(r"[\s,]", "", str(s or "")).rstrip(".")


def cands(which):
    out = []
    for m, tag in SRC:
        for s in (1, 2, 3):
            p = f"{R}/{which}_{tag}_progc_s{s}.jsonl"
            for l in (open(p) if os.path.exists(p) else []):
                r = json.loads(l)
                c = r.get("code") or ""
                sig = re.search(r"def solve\(\s*(\w+)\s*(?:=[^,)]*)?\)", c)
                call = re.search(r"__main__.*?(solve\([^\n]*\))", c, re.S)
                out.append({"id": r["id"], "src": f"{m}_s{s}", "answer": norm(r.get("answer")), "right": str(r["correct"]) == "True",
                            "tok": int(r.get("out_tokens") or 0), "arg": sig.group(1) if sig else None,
                            "call": call.group(1)[:120] if call else None, "code": c})
    return out


def build(which):
    from sandbox import run_python
    C = [c for c in cands(which) if c["arg"]]
    def one(c):
        r = run_python("__name__ = '__sweep__'\n" + c["code"] + SWEEP, "", timeout=60, mem_bytes=4 << 30)
        vals = {}
        for l in (r.stdout or "").splitlines():
            if l.startswith("__SW__"):
                _, n, v = l.split(" ", 2); vals[n] = v
        return {"id": c["id"], "src": c["src"], "vals": vals}
    with ThreadPoolExecutor(int(os.environ.get("XV_PAR", 14))) as ex, open(f"{R}/pe_diff_sweep_{which}.jsonl", "w") as f:
        for o in ex.map(one, C):
            f.write(json.dumps(o) + "\n"); f.flush()


def boxed(t):
    m = re.findall(r"\\boxed\{([^{}]*)\}", t or "")
    return norm(m[-1]) if m else None


def run(which):
    from llm import chat
    P = {p["id"]: p for p in json.load(open(f"{DATA}/{'euler_dev' if which == 'euler' else 'euler_test'}.json"))}
    C = cands(which)
    SW = {(x["id"], x["src"]): x["vals"] for x in map(json.loads, open(f"{R}/pe_diff_sweep_{which}.jsonl"))}
    by = defaultdict(list)
    for c in C:
        by[c["id"]].append(c)
    tag = os.environ.get("DIFF_TAG", "")
    out = f"{R}/pe_diff_{which}{tag}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()

    def one(pid):
        cs = by[pid]
        cls = defaultdict(list)
        for c in cs:
            if c["answer"]:
                cls[c["answer"]].append(c)
        plural = max(cls, key=lambda k: len(cls[k])) if cls else None
        rounds, otok = [], 0
        alive = dict(cls)
        for _ in range(3):
            if len(alive) < 2:
                break
            # class value at n = the value shared by its swept members (first one with a sweep)
            def val(k, n):
                for c in alive[k]:
                    v = SW.get((pid, c["src"]), {}).get(str(n))
                    if v not in (None, "TIMEOUT", "error"):
                        return norm(v)
                return None
            n = next((n for n in range(1, 13) if len({val(k, n) for k in alive if val(k, n) is not None}) > 1), None)
            if n is None:
                break
            ref = next(c for k in alive for c in alive[k] if c["arg"] and val(k, n) is not None)
            o = chat(ASK.format(p=P[pid]["problem"], arg=ref["arg"], call=ref["call"] or f"solve(...)", n=n), think=True, max_tokens=16000,
                     temperature=0.7, seed=500 + n)
            otok += o.get("out_tokens") or 0; v = boxed(o.get("text"))
            keep = {k: alive[k] for k in alive if val(k, n) == v}
            rounds.append({"n": n, "oracle": v, "kept": len(keep), "of": len(alive)})
            if not keep:
                break
            alive = keep
        pick = max(alive, key=lambda k: len(alive[k])) if alive else None
        right = lambda k: bool(k) and any(c["right"] for c in cls.get(k, []))
        return {"id": pid, "right": right(pick), "plurality_right": right(plural), "any_right": any(c["right"] for c in cs),
                "pool_tok": sum(c["tok"] for c in cs), "oracle_tok": otok, "rounds": rounds}

    todo = [p for p in by if p not in done]
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for r in ex.map(one, todo):
            f.write(json.dumps(r) + "\n"); f.flush()


def score():
    import random
    for fn in sorted(os.listdir(R)):
        if not (fn.startswith("pe_diff_euler") and "sweep" not in fn):
            continue
        Rw = [json.loads(l) for l in open(f"{R}/{fn}")]; n = len(Rw)
        U = lambda ok, t: 100 * ok - 0.5 * t / 1000
        d = {r["id"]: U(r["right"], r["pool_tok"] + r["oracle_tok"]) - U(r["plurality_right"], r["pool_tok"]) for r in Rw}
        acc = {r["id"]: 100 * (r["right"] - r["plurality_right"]) for r in Rw}
        ids = list(d); rng = random.Random(1); B = 4000
        bs = sorted(sum(acc[rng.choice(ids)] for _ in ids) / n for _ in range(B))
        print(f"{fn}: n={n} DIFF {100*sum(r['right'] for r in Rw)/n:.1f}% plurality {100*sum(r['plurality_right'] for r in Rw)/n:.1f}% any "
              f"{100*sum(r['any_right'] for r in Rw)/n:.1f}%  oracle {sum(r['oracle_tok'] for r in Rw)/n/1000:.2f}k  accuracy gain "
              f"{sum(acc.values())/n:+.2f} [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)-1]:+.2f}]  utility gain {sum(d.values())/n:+.2f}")


if __name__ == "__main__":
    {"build": lambda: build(sys.argv[2]), "run": lambda: run(sys.argv[2]), "score": score}[sys.argv[1]]()
