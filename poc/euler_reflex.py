"""REFLEX-E (PREREG_DIFF, 2026-11-27): Reflexion-style second attempt (2303.11366) for Project Euler attempts PROV flags, against PROV2's
independent second attempt. First attempts = attempt A of the CONF-E2 rows (tirdis2_*_s16_17); for each A that PROV flags, a fresh native-tool
session (tir_native's harness, Euler prompt) gets the problem plus A's final message and the fact that its answer was never printed by a tool run.
PROV2's second attempt on the same problems is attempt B of the same rows (seed 17, independent). usage: POC_BASE_URL=... python euler_reflex.py run | score
Temporary files: each session's sandbox is removed by Session.close()."""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
from tir_dispute import Session
R = T.R; PAIR = os.environ.get("REFL_PAIR", "16_17"); RS = int(os.environ.get("REFL_SEED", 18)); OUT = f"{R}/eulrefl_s{RS}.jsonl"
NOTE = ("\n\nA previous attempt at this problem ended with the final message below. Its answer {a} was never printed by any of its tool runs, so it was "
        "not actually computed and is probably wrong. Solve the problem again from the start; if the previous approach was too slow or did not finish, "
        "use a different method.\n\nPrevious final message:\n{f}")


def rows():
    out = []
    for st in ("euler", "eulert"):
        P, prompt, grade = T.task(st); PP = {p["id"]: p for p in P}
        for l in open(f"{R}/{os.environ.get('REFL_PREFIX', 'tirdis2')}_{st}_medium_s{PAIR}.jsonl"):
            z = json.loads(l); out.append((st, PP[z["id"]], prompt, grade, z))
    return out


def run():
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
    todo = [x for x in rows() if x[4]["A"]["flag"] and x[1]["id"] not in done]
    def one(x):
        st, p, prompt, grade, z = x
        s = Session(prompt(p) + NOTE.format(a=z["A"]["ans"] or "(none)", f=(z["A"]["final"] or "")[-1500:]), "medium", RS * 1000 + zlib.crc32(p["id"].encode()) % 997, tok)
        try:
            f = s.gen(T.CAP)
        finally:
            s.close()
        pv = T.provenance({"final": f, "outs": s.outs}) if f else None
        return {"id": p["id"], "set": st, "final": (f or "")[-2000:], "out_tokens": s.used, "calls": s.calls, "finish": s.fin, "flag": (not pv) or s.fin != "stop", **grade(p, f or "")}
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(OUT, "a") as fo:
        for fu in as_completed([ex.submit(one, x) for x in todo]):
            fo.write(json.dumps(fu.result()) + "\n"); fo.flush()
    print("REFLEX rows", sum(1 for _ in open(OUT)), flush=True)


def score():
    import tir_score as S, ma_effort as M, run_compute as RC
    U = S.U; X = {json.loads(l)["id"]: json.loads(l) for l in open(OUT)}
    g = {p["id"]: p["answer"] for st in ("euler", "eulert") for p in RC.problems(st)}
    ok = lambda r, i: float((lambda a: bool(a) and RC.norm(a) == RC.norm(g[i]))(M.ans(r.get("final", "")) or ""))
    A1, A2, d = {}, {}, []; fl = []
    for st, p, prompt, grade, z in rows():
        i = p["id"]; a, b = z["A"], z["B"]
        if not a["flag"]:
            A1[i] = A2[i] = (ok(a, i), a["out_tokens"]); continue
        r = X.get(i)
        if r is None:
            continue
        A1[i] = ((ok(b, i) if not b["flag"] else ok(a, i)), a["out_tokens"] + b["out_tokens"])       # PROV2: B replaces A when B is not flagged
        A2[i] = ((ok(r, i) if not r["flag"] else ok(a, i)), a["out_tokens"] + r["out_tokens"])       # REFLEX: the informed attempt, same rule
        fl.append((ok(a, i), ok(b, i), ok(r, i), b["out_tokens"], r["out_tokens"], b["flag"], r["flag"]))
    ks = sorted(set(A1) & set(A2))
    for n, D in (("PROV2 (independent 2nd)", A1), ("PROV2-REFLEX", A2)):
        print(f"{n:24s} {100*sum(D[k][0] for k in ks)/len(ks):.1f}% @ {sum(D[k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*D[k]) for k in ks)/len(ks):.2f}")
    print("REFLEX − PROV2 (all", len(ks), "):", "utility", S.ci([U(*A2[k]) - U(*A1[k]) for k in ks]), "accuracy", S.ci([100 * (A2[k][0] - A1[k][0]) for k in ks]))
    n = len(fl)
    print(f"on the {n} flagged first attempts: first right {sum(x[0] for x in fl):.0f}; independent 2nd right {sum(x[1] for x in fl):.0f} @ {sum(x[3] for x in fl)/n/1000:.1f}k (flagged {sum(x[5] for x in fl)}); "
          f"reflexion 2nd right {sum(x[2] for x in fl):.0f} @ {sum(x[4] for x in fl)/n/1000:.1f}k (flagged {sum(x[6] for x in fl)})")


if __name__ == "__main__":
    {"run": run, "score": score}[sys.argv[1]]()
