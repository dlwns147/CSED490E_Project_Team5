"""PREREG_DIFF addendum PE-R (2026-11-23): one repair turn for a Project Euler think-then-solve() program that visibly fails — it crashes,
runs out of time / memory, or fails one of the small cases the statement itself gives (CHECKS). The model gets the problem, its program
and the evidence (the error, or each failing check as stated vs computed) and writes a corrected program in the same format; the repaired
answer replaces the original when the repaired program runs and passes its checks (or has none), else the original stands.
usage: POC_BASE_URL=... python pe_repair.py run <euler|eulert> <tag> <seed>   |   python pe_repair.py score"""
import json, os, random, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f"{ROOT}/results/x44"
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute")
FIX = ("{task}\n\nYour earlier program for this problem:\n```python\n{code}\n```\n{evidence}\nFind the mistake and write the corrected program in the "
       "same format (solve(...), CHECKS, and the main block printing only the answer). It must finish within one minute. Give it in a single "
       "```python code block.")


def evidence(r):
    if r.get("status") != "ok":
        return f"When run, it did not finish correctly (status: {r.get('status')})."
    bad = [c for c in (r.get("checks") or []) if c[-1] is not True]
    return "It fails these small cases that the statement itself gives:\n" + "\n".join(
        f"- arguments {c[0]}: the statement says {c[1]}, your program computed {c[2]}" for c in bad)


def visible_fail(r):
    ck = r.get("checks")
    return r.get("status") != "ok" or (isinstance(ck, list) and ck and not all(c[-1] is True for c in ck))


def run(which, tag, seed):
    from llm import chat, last_block
    import run_compute as RC
    P = {p["id"]: p for p in json.load(open(f"{DATA}/{'euler_dev' if which == 'euler' else 'euler_test'}.json"))}
    rows = [json.loads(l) for l in open(f"{R}/{which}_{tag}_thinkpc_s{seed}.jsonl")]
    out = f"{R}/{which}_{tag}_thinkpcR_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    todo = [r for r in rows if r.get("code") and visible_fail(r) and r["id"] not in done]

    def one(r):
        task = RC.EULER_PROGC.format(p=P[r["id"]]["problem"])
        o = chat(FIX.format(task=task, code=r["code"].strip(), evidence=evidence(r)), think=True, max_tokens=16000, temperature=0.7,
                 seed=seed * 1000 + zlib.crc32(r["id"].encode()) % 997 + 31)
        code = last_block(o.get("text") or "", ("python", "py", "python3"))
        x = RC.run_python(code, "", timeout=RC.PROG_S, mem_bytes=4 << 30) if code else None
        outp = ((x.stdout if x and x.status == "ok" else "") or "").strip()
        ans = outp.splitlines()[-1] if outp else ""
        checks, cst = RC.run_checks(code) if code else (None, "no_code")
        return {"id": r["id"], "out_tokens": o.get("out_tokens"), "status": (x.status if x else "no_code"), "answer": ans,
                "checks": checks, "correct": bool(ans) and RC.norm(ans) == RC.norm(P[r["id"]]["answer"]), "code": code}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for z in ex.map(one, todo):
            f.write(json.dumps(z) + "\n"); f.flush()


TAGM = os.environ.get("PE_TAG", "oss120")


def score():
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    for which in ("euler", "eulert"):
        base, rep = {}, {}
        for s in (1, 2, 3):
            F = {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{which}_{TAGM}_thinkpc_s{s}.jsonl")}
            p = f"{R}/{which}_{TAGM}_thinkpcR_s{s}.jsonl"
            Rr = {json.loads(l)["id"]: json.loads(l) for l in open(p)} if os.path.exists(p) else {}
            for i, r in F.items():
                t = int(r.get("out_tokens") or 0); ok = str(r["correct"]) == "True"
                base.setdefault(i, []).append(U(ok, t))
                z = Rr.get(i)
                if z is None:
                    rep.setdefault(i, []).append(U(ok, t)); continue
                t2 = t + int(z.get("out_tokens") or 0)
                zok = z.get("status") == "ok" and z.get("answer") and (not z.get("checks") or all(c[-1] is True for c in z["checks"]))
                rep.setdefault(i, []).append(U(z["correct"] if zok else ok, t2))
        ids = sorted(base); d = {i: sum(rep[i]) / len(rep[i]) - sum(base[i]) / len(base[i]) for i in ids}
        rng = random.Random(1); B = 4000
        bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(B))
        print(f"{which}: thinkpc U {sum(sum(base[i])/len(base[i]) for i in ids)/len(ids):.2f}  +repair U {sum(sum(rep[i])/len(rep[i]) for i in ids)/len(ids):.2f}  "
              f"diff {sum(d.values())/len(ids):+.2f} [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)-1]:+.2f}] p={(sum(x<=0 for x in bs)+1)/(B+1):.4f}")


if __name__ == "__main__":
    run(sys.argv[2], sys.argv[3], int(sys.argv[4])) if sys.argv[1] == "run" else score()
