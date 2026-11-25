"""PREREG_DIFF addendum MC-R (2026-11-23): one repair turn for a MathConstruct progc program whose own verify() fails (or that crashes),
before falling back to think-then-program. The model gets the problem, its program and the evidence (verify() returned False on its
construction, or the error); the repaired program is run (construct + verify); its construction is used if its verify() passes.
Policy compared: own-verify ladder (progc; if verify fails, think-then-program) vs ladder + repair (progc; if verify fails, repair; if
the repair's verify fails too, think-then-program). usage: POC_BASE_URL=... python mcon_repair.py run <tag> <seed> | score"""
import json, os, random, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
SET = os.environ.get("MC_SET", "mcon")   # mconf: fresh parameters (addendum MC-R-F)
FIX = ("{task}\n\nYour earlier program for this problem:\n```python\n{code}\n```\n{evidence}\nFind the mistake (in the construction or in "
       "verify) and write the corrected program in the same format. Give it in a single ```python code block.")


def run(tag, seed):
    from llm import chat, last_block
    import run_compute as RC
    P = {p["id"]: p for p in RC.problems(SET)}
    rows = [json.loads(l) for l in open(f"{R}/{SET}_{tag}_progc_s{seed}.jsonl")]
    out = f"{R}/{SET}_{tag}_progcR{os.environ.get('MC_RSFX', '')}_s{seed}.jsonl"   # MC_RSFX: e.g. "low" (addendum MC-RL)
    todo = [r for r in rows if r.get("code") and str(r.get("verify")) != "True"]

    def one(r):
        ev = (f"When run, it did not finish correctly (status: {r.get('status')})." if r.get("status") != "ok"
              else "Your own verify() returned False for the object your construct() built, so the construction does not meet the conditions.")
        o = chat(FIX.format(task=RC.MC_PROGC.format(p=P[r["id"]]["problem"]), code=r["code"].strip(), evidence=ev), think=True,
                 max_tokens=16000, temperature=0.7, seed=seed * 1000 + zlib.crc32(r["id"].encode()) % 997 + 41)
        code = last_block(o.get("text") or "", ("python", "py", "python3"))
        x = RC.run_python(code, "", timeout=RC.PROG_S, mem_bytes=4 << 30) if code else None
        ans = ((x.stdout if x and x.status == "ok" else "") or "").strip().replace("\x08", "\\b")
        ver = None
        if code:
            rv = RC.run_python("__name__ = '__check__'\n" + code + "\n\nprint('__VERIFY__', bool(verify(construct())))\n", "", timeout=RC.PROG_S, mem_bytes=4 << 30)
            m = re.search(r"__VERIFY__ (True|False)", rv.stdout or "")
            ver = (m.group(1) == "True") if (rv.status == "ok" and m) else None
        try:
            _, ok, _ = RC._MC[r["id"]].parse_and_check([{"role": "assistant", "content": ans}]) if ans else (None, False, "")
        except Exception:
            ok = False
        return {"id": r["id"], "out_tokens": o.get("out_tokens"), "verify": ver, "correct": bool(ok)}
    with ThreadPoolExecutor(32) as ex, open(out, "w") as f:
        for z in ex.map(one, todo):
            f.write(json.dumps(z) + "\n"); f.flush()


def score():
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    for tag in ("oss120", "oss20"):
        lad, rep = {}, {}
        for s in (1, 2, 3):
            pp = f"{R}/{SET}_{tag}_progcR_s{s}.jsonl"
            if not os.path.exists(pp):
                continue
            C = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{SET}_{tag}_progc_s{s}.jsonl")}
            T = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{SET}_{tag}_thinkp_s{s}.jsonl")}
            Z = {json.loads(l)["id"]: json.loads(l) for l in open(pp)}
            for i, c in C.items():
                if i not in T:
                    continue
                tc, tt = int(c.get("out_tokens") or 0), int(T[i].get("out_tokens") or 0); okt = str(T[i]["correct"]) == "True"
                if str(c.get("verify")) == "True":
                    u = U(str(c["correct"]) == "True", tc); lad.setdefault(i, []).append(u); rep.setdefault(i, []).append(u); continue
                lad.setdefault(i, []).append(U(okt, tc + tt))
                z = Z.get(i)
                if z and z.get("verify") is True:
                    rep.setdefault(i, []).append(U(z["correct"], tc + int(z.get("out_tokens") or 0)))
                else:
                    rep.setdefault(i, []).append(U(okt, tc + (int(z.get("out_tokens") or 0) if z else 0) + tt))
        if not lad:
            continue
        ids = sorted(lad); d = {i: sum(rep[i]) / len(rep[i]) - sum(lad[i]) / len(lad[i]) for i in ids}
        rng = random.Random(1); B = 4000
        bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B))
        print(f"{tag}: ladder U {sum(sum(lad[i])/len(lad[i]) for i in ids)/len(ids):.2f}  ladder+repair U {sum(sum(rep[i])/len(rep[i]) for i in ids)/len(ids):.2f}  "
              f"diff {sum(d.values())/len(ids):+.2f} [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)-1]:+.2f}] p={(sum(x<=0 for x in bs)+1)/(B+1):.4f}")


if __name__ == "__main__":
    run(sys.argv[2], int(sys.argv[3])) if sys.argv[1] == "run" else score()
