"""LC-1 (docs/prereg/PREREG_LC.md): grade run_lcb.py's programs with the official LiveCodeBench grader (lcb_runner/evaluation/
testing_util.run_test from github.com/LiveCodeBench/LiveCodeBench @28fef95, cloned to $POC_DATA/lcb/LiveCodeBench; loaded by path so the
package's other imports are not needed), timeout 6 s per test, its global timeout per program. Tests run public first, then hidden (the
official order); the grader stops at the first failure, so one run gives both:
  chk = the free check: a program was extracted and it passes every sample (public) test
  ok  = the grade: it passes every test (pass@1)
  err = where and how it first failed: nocode | pub/priv + WA (-2) / TLE (-3) / RE (-4) / compile (-1 or None)
Code is extracted as LiveCodeBench does for chat models (between the last two lines holding ```). Arms: N (cheap.n_text), T, SB.
Runs in the project image on a CPU partition (the programs are untrusted; the grader disables os functions in a child process):
  sbatch -J lcb_grade -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none --cpus-per-task=16 poc/slurm/job.sh '$P poc/grade_lcb.py q8b'
usage: python grade_lcb.py <tag> [seeds]   -> results/lcb/grades_<tag>_s<seed>.json (resumes)
  LCB_RECHECK=1 LCB_WORKERS=4: regrade the time-limit failures at low load (a graded program's 'recheck'; the grade is unchanged)"""
import importlib.util, json, multiprocessing, os, sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import _rows  # noqa: E402

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(50000)   # as compute_code_generation_metrics.py
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "lcb")
LCB = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "lcb")
TIMEOUT = 6
RECHECK = os.environ.get("LCB_RECHECK") == "1"
_spec = importlib.util.spec_from_file_location("lcb_testing_util", f"{LCB}/LiveCodeBench/lcb_runner/evaluation/testing_util.py")
tu = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(tu)


def extract_code(text):
    lines = (text or "").split("\n")
    ix = [i for i, l in enumerate(lines) if "```" in l]
    return "\n".join(lines[ix[-2] + 1: ix[-1]]) if len(ix) >= 2 else ""


def _temp_run(sample, generation, result):
    res, _ = tu.run_test(sample, test=generation, debug=False, timeout=TIMEOUT)
    result.append(res)


def check_correctness(sample, generation, n_tests):
    """as lcb_runner's check_correctness: the run in a child process, killed after (timeout + 1) x tests + 5 s (= all tests failed)"""
    manager = multiprocessing.Manager()
    result = manager.list()
    p = multiprocessing.Process(target=_temp_run, args=(sample, generation, result))
    p.start()
    p.join(timeout=(TIMEOUT + 1) * n_tests + 5)
    if p.is_alive():
        p.kill()
    out = list(result[0]) if result else [-1] * n_tests
    manager.shutdown()
    out = [bool(e) if type(e).__name__ in ("bool_", "bool") else (e.item(0) if hasattr(e, "item") else e) for e in out]
    return [-2 if e is False else e for e in out]   # a call-based wrong answer is recorded as False


def grade(key, code, t):
    if not code.strip():
        return key, {"ok": False, "chk": False, "err": "nocode"}
    sample = {"input_output": json.dumps({"inputs": t["inputs"], "outputs": t["outputs"], "fn_name": t["fn_name"]})}
    res = check_correctness(sample, code, len(t["inputs"]))
    npass = next((i for i, e in enumerate(res) if e is not True), len(res))
    ok = npass == len(t["inputs"])
    err = None if ok else f"{'pub' if npass < t['n_pub'] else 'priv'}{res[npass] if npass < len(res) else 'short'}"
    return key, {"ok": ok, "chk": npass >= t["n_pub"], "err": err, "npass": npass}


def main():
    tag, seeds = sys.argv[1], [int(s) for s in (sys.argv[2:] or ["1", "2", "3"])]
    T = {}
    for l in open(f"{LCB}/lcb_tests.jsonl"):
        r = json.loads(l); T[r["id"]] = r
    workers = int(os.environ.get("LCB_WORKERS", len(os.sched_getaffinity(0))))
    for s in seeds:
        gp = f"{RES}/grades_{tag}_s{s}.json"
        G = json.load(open(gp)) if os.path.exists(gp) else {}
        rows = {"N": {r["id"]: r.get("n_text") for r in _rows(f"{RES}/{tag}_cheap_s{s}.jsonl")},
                "T": {r["id"]: r.get("text") for r in _rows(f"{RES}/{tag}_think_s{s}.jsonl")},
                "SB": {r["id"]: r.get("text") for r in _rows(f"{RES}/{tag}_sb_s{s}.jsonl")}}
        todo = [((i, a), extract_code(x)) for a, R in rows.items() for i, x in R.items() if a not in G.get(i, {})]
        if RECHECK:   # time-limit check: regrade every program that failed by time limit, at LCB_WORKERS (low load)
            todo = [((i, a), extract_code(rows[a][i])) for i, g in G.items() for a in g if (g[a]["err"] or "").endswith("-3")
                    and "recheck" not in g[a]]
        with ProcessPoolExecutor(workers) as ex:
            fus = [ex.submit(grade, k, c, T[k[0]]) for k, c in todo]
            for n, fu in enumerate(as_completed(fus), 1):
                (i, a), g = fu.result()
                if RECHECK:
                    G[i][a]["recheck"] = g
                else:
                    G.setdefault(i, {})[a] = g
                if n % 200 == 0:
                    json.dump(G, open(gp, "w"))
        json.dump(G, open(gp, "w"))
        if RECHECK:
            r = [G[i][a] for i in G for a in G[i] if "recheck" in G[i][a]]
            print(tag, s, f"time-limit recheck: {len(r)} programs, still time limit {sum(x['recheck']['err'] == x['err'] for x in r)}, "
                  f"now pass {sum(x['recheck']['ok'] for x in r)}, other {sum(x['recheck']['err'] not in (None, x['err']) for x in r)}",
                  flush=True)
            continue
        for a in rows:
            v = [G[i][a] for i in G if a in G[i]]
            print(tag, s, a, f"n {len(v)} ok {sum(x['ok'] for x in v)} chk {sum(x['chk'] for x in v)} "
                  f"leak {sum(x['chk'] and not x['ok'] for x in v)}", flush=True)


if __name__ == "__main__":
    main()
