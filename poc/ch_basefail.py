"""CH: failure kinds (WA / RE / TLE / no code) of the existing medium runs, which did not record them: re-run each failing stored program on
its first failing test (index = passed). usage: CC_SET=full python ch_basefail.py  -> results/h2/ch_basefail_<tag>_s<seed>.jsonl"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import PFILE, VFILE, RES, tok_eq, tests_of  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}
V = json.load(open(VFILE))
for tag in ("oss120_medium", "oss20_medium"):
    for s in (1, 2, 3):
        path = f"{RES}/ch_basefail_{tag}_s{s}.jsonl"
        if os.path.exists(path):
            continue
        R = [json.loads(l) for l in open(f"{RES}/cc_full_{tag}_s{s}.jsonl")]

        def kind(r):
            if r["passed_all"]:
                return "pass"
            if not r["code"]:
                return "no_code"
            t = tests_of(P[r["name"]])[r["passed"]]
            x = run_python(r["code"], t["input"], timeout=10)
            return "WA" if x.status == "ok" else "TLE" if x.status == "tle" else "RE"
        with ThreadPoolExecutor(16) as ex:
            K = list(ex.map(kind, R))
        with open(path, "w") as f:
            for r, k in zip(R, K):
                f.write(json.dumps({"name": r["name"], "fail": k}) + "\n")
        print(tag, s, {k: K.count(k) for k in set(K)}, flush=True)
