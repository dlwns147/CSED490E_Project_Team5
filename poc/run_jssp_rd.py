"""N14c (results/PREREG_N14.md): job-shop with RELEASE DATES (one added rule) on la01-la40. Job j may not start its first operation
before r_j (r_j drawn once per instance: uniform 0 .. half of job j's total processing time, seed "rd-<name>-<j>"). Input = the H5
format plus a final line with the n release dates. Checker = H5 checker + release dates. Reference = CP-SAT (8 workers, 120 s).
Conditions: from scratch, or adapting a source program (--adapt FILE --note TEXT) appended to the prompt.
usage: python run_jssp_rd.py prep | ref
       POC_BASE_URL=... python run_jssp_rd.py run <tag> <seed> [--adapt FILE --note TEXT] [--max_tokens N]
       python run_jssp_rd.py pick <h5 tag> -> results/h5/rd/src_<tag>_{good,bad}.py (verified on the 8 H5 training instances)"""
import json, os, random, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_jssp as J  # noqa: E402
from sandbox import run_python  # noqa: E402

RD = f"{J.RES}/rd"
TRAIN = ["la01", "la06", "la11", "la16", "la21", "la26", "la31", "la36"]


def releases(name):
    n, m, jobs = J.load(name)
    return [random.Random(f"rd-{name}-{j}").randint(0, sum(d for _, d in jobs[j]) // 2) for j in range(n)]


def prep():
    os.makedirs(f"{RD}/instances", exist_ok=True)
    for name in J.names():
        base = open(f"{J.RES}/instances/{name}.txt").read().strip()
        open(f"{RD}/instances/{name}.txt", "w").write(base + "\n" + " ".join(map(str, releases(name))) + "\n")
    print(len(J.names()), "instances written")


def check(name, out):
    ok, ms, why = J.check(name, out)
    if not ok:
        return ok, ms, why
    S = [list(map(int, l.replace(",", " ").split())) for l in out.strip().split("\n") if l.strip()]
    if any(S[j][0] < r for j, r in enumerate(releases(name))):
        return False, None, "release date"
    return ok, ms, why


STATEMENT = J.STATEMENT.replace(
    "every job visits every machine exactly once).",
    "every job visits every machine exactly once); the LAST line has n integers r_0 ... r_{n-1}, the release dates of the jobs.").replace(
    "Rules: each operation", "Rules: job j may not start its first operation before its release date r_j; each operation")
assert STATEMENT != J.STATEMENT and "release dates" in STATEMENT and "before its release date" in STATEMENT

REF = J.REF.replace('n, m = L[0]; jobs', 'n, m = L[0]; rel = L[n + 1]; jobs').replace(
    "        if k: md.Add(s >= st[j, k - 1] + jobs[j][k - 1][1])",
    "        if k: md.Add(s >= st[j, k - 1] + jobs[j][k - 1][1])\n        else: md.Add(s >= rel[j])")
assert "rel[j]" in REF


def score(name, code, timeout):
    r = run_python(code, open(f"{RD}/instances/{name}.txt").read(), timeout=timeout, mem_bytes=8 << 30, cpu_s=64 * timeout)
    if r.status != "ok":
        return {"feasible": False, "reason": r.status, "makespan": None, "stderr": (r.stderr or "")[-600:]}
    ok, ms, why = check(name, r.stdout)
    return {"feasible": ok, "reason": why, "makespan": ms, "stderr": (r.stderr or "")[-200:]}


def ref():
    with ThreadPoolExecutor(3) as ex:
        out = dict(zip(J.names(), ex.map(lambda n: score(n, REF, 200), J.names())))
    json.dump(out, open(f"{RD}/ref.json", "w"), indent=1)
    print({n: (v["makespan"], v["stderr"].strip()[-20:]) for n, v in out.items()})


def pick(tag):
    """good = the H5 program (2 seeds, training instances) feasible on the most of the 8 H5 training instances (ties: lower mean
    makespan / H5 reference); bad = a program of the same pool that runs but is infeasible on its own instance."""
    href = {n: v["makespan"] for n, v in json.load(open(f"{J.RES}/ref.json")).items()}
    pool = [r for sd in (1, 2) for r in map(json.loads, open(f"{J.RES}/sol_{tag}_s{sd}.jsonl")) if r["name"] in TRAIN and r.get("code")]
    good_c = [r for r in pool if r["feasible"]]
    def ev(r):
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(lambda n: J.score(n, r["code"], J.TLIM + 30), TRAIN))
        f = [(n, v) for n, v in zip(TRAIN, res) if v["feasible"]]
        return len(f), (sum(v["makespan"] / href[n] for n, v in f) / len(f) if f else 9)
    keys = [ev(r) for r in good_c[:6]]
    i = max(range(len(keys)), key=lambda k: (keys[k][0], -keys[k][1]))
    os.makedirs(RD, exist_ok=True)
    open(f"{RD}/src_{tag}_good.py", "w").write(good_c[i]["code"])
    bad = [r for r in pool if not r["feasible"] and r["reason"] not in ("no code", "tle")]
    if bad:
        open(f"{RD}/src_{tag}_bad.py", "w").write(bad[0]["code"])
    print(tag, "good: feasible on", keys[i][0], "/ 8 training, mean ms/ref", round(keys[i][1], 4), "| bad:", bad[0]["reason"] if bad else None)


def run(tag, seed, maxtok, adapt=None, note=""):
    from llm import chat, last_block
    p = STATEMENT.replace("{T}", str(J.TLIM))
    if adapt:
        p += (f"\n\nBelow is a Python program that {note}. Use it as your starting point and adapt it to THIS problem (keep what still "
              f"applies, change what the new problem requires):\n```python\n{open(adapt).read()}\n```")
        if MINIMAL:   # N14d
            p += "\nChange as few lines as possible: keep every line that is unrelated to the new rule exactly as it is."

    def one(name):
        o = chat(p, temperature=0.7, max_tokens=maxtok, seed=seed * 1000 + zlib.crc32(name.encode()) % 997)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        s = score(name, code, J.TLIM + 30) if code else {"feasible": False, "reason": "no code", "makespan": None, "stderr": ""}
        return {"name": name, **s, "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), "code": code}

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, J.names()))
    with open(f"{RD}/sol_{tag}_s{seed}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(tag, seed, f"feasible {sum(r['feasible'] for r in rows)}/{len(rows)}", flush=True)


MINIMAL = "--minimal" in sys.argv

if __name__ == "__main__":
    a = sys.argv
    mt = int(a[a.index("--max_tokens") + 1]) if "--max_tokens" in a else 8000
    if a[1] == "prep":
        prep()
    elif a[1] == "ref":
        ref()
    elif a[1] == "pick":
        pick(a[2])
    elif a[1] == "run":
        run(a[2], int(a[3]), mt, a[a.index("--adapt") + 1] if "--adapt" in a else None, a[a.index("--note") + 1] if "--note" in a else "")
