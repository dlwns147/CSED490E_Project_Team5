"""JUDGE-MC (PREREG_DIFF, 2026-11-27): the S* / GenSelect-style baseline (2502.14382, 2511.13027) on MathConstruct constructions — a fresh native-tool
session is shown the problem and the two submitted answers of the CONF-MC attempts (OWN-E, seeds 5 / 6) and picks one (python allowed, e.g. to test
the stated conditions). Completes the selection map: free signals fail on constructions (CONF-MC); does a paid judge succeed? Order of A / B set by
crc32 parity (balanced), position reported. usage: TIR_ENV=1 POC_BASE_URL=... python mc_judge.py run | score
Temporary files: each judge session's sandbox is removed by Session.close()."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_native as T
from tir_dispute import Session
R = T.R; SA, SB = (int(x) for x in os.environ.get("JSEEDS", "5,6").split(",")); JP = os.environ.get("JPREFIX", "tirsublp"); JSET = os.environ.get("JSET", "mcong"); OUTF = f"{R}/mcjudge{'' if JP == 'tirsublp' else '_' + JP}{'' if JSET == 'mcong' else '_' + JSET}_s{SA}_{SB}.jsonl"
Q = ("{p}\n\nTwo candidate answers have been submitted for this problem.\n\nCandidate A:\n{a}\n\nCandidate B:\n{b}\n\nExactly one of them may be correct. "
     "Determine which one satisfies every condition of the problem; you may use the python tool to test the conditions. Reply with the single letter of the correct candidate in \\boxed{{}}.")


def pairs():
    L = lambda s: {z["id"]: z for z in map(json.loads, open(f"{R}/{JP}_OWN_{JSET}_medium_s{s}.jsonl"))}
    A, B = L(SA), L(SB); P, prompt, grade = T.task(JSET); PP = {p["id"]: p for p in P}
    return [(PP[k], A[k], B[k]) for k in sorted(set(A) & set(B)) if k in PP], prompt


def run():
    import llm
    tok = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    P, prompt = pairs(); done = {json.loads(l)["id"] for l in open(OUTF)} if os.path.exists(OUTF) else set()
    def one(x):
        p, a, b = x; h = zlib.crc32(p["id"].encode()); swap = h % 2 == 1; first, second = (b, a) if swap else (a, b)
        if a["final"].strip() == b["final"].strip():
            return {"id": p["id"], "same": True, "pick": "A", "out_tokens": 0, "swap": swap}
        s = Session(Q.format(p=prompt(p), a=first["final"][-1500:], b=second["final"][-1500:]), "medium", 31000 + h % 997, tok)
        try:
            f = s.gen(T.CAP)
        finally:
            s.close()
        m = re.findall(r"\\boxed\{\s*\(?([AB])\)?\s*\}", f or ""); letter = m[-1] if m else ""
        chosen = {"A": first, "B": second}.get(letter)
        return {"id": p["id"], "same": False, "swap": swap, "letter": letter, "chosen_seed": (SB if chosen is b else SA) if chosen else None, "out_tokens": s.used, "calls": s.calls, "finish": s.fin}
    with ThreadPoolExecutor(int(os.environ.get("TIR_WORKERS", 48))) as ex, open(OUTF, "a") as fo:
        for fu in as_completed([ex.submit(one, x) for x in P if x[0]["id"] not in done]):
            fo.write(json.dumps(fu.result()) + "\n"); fo.flush()
    print("JUDGE-MC rows", sum(1 for _ in open(OUTF)), flush=True)


def score():
    import tir_score as S
    U = S.U; P, _ = pairs(); J = {z["id"]: z for z in map(json.loads, open(OUTF))}; arms = {"ONE": {}, "JUDGE": {}, "ORACLE2": {}}; one_right = []
    for p, a, b in P:
        if p["id"] not in J:
            continue
        j = J[p["id"]]; c = lambda z: float(bool(z["correct"])); ta, tb = a["out_tokens"], b["out_tokens"]
        arms["ONE"][p["id"]] = ((c(a) + c(b)) / 2, (ta + tb) / 2)
        arms["ORACLE2"][p["id"]] = (max(c(a), c(b)), ta + tb)
        pick = (b if j.get("chosen_seed") == SB else a) if j.get("chosen_seed") else a
        arms["JUDGE"][p["id"]] = (c(pick), ta + tb + j["out_tokens"])
        if c(a) != c(b):
            one_right.append((j, (SA if c(a) else SB)))
    ks = list(arms["ONE"]); key = [k.split("__")[0] for k in ks]
    for n, d in arms.items():
        print(f"{n:8s} {100*sum(d[k][0] for k in ks)/len(ks):.1f}% @ {sum(d[k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*d[k]) for k in ks)/len(ks):.2f}")
    one = sum(arms["ONE"][k][0] for k in ks); orc = sum(arms["ORACLE2"][k][0] for k in ks)
    print(f"share of the room captured by JUDGE: {(sum(arms['JUDGE'][k][0] for k in ks)-one)/max(1e-9, orc-one):.2f}")
    print(f"JUDGE − ONE: accuracy {S.ci([100*(arms['JUDGE'][k][0]-arms['ONE'][k][0]) for k in ks], key)} utility {S.ci([U(*arms['JUDGE'][k])-U(*arms['ONE'][k]) for k in ks], key)}")
    w = sum(j.get("chosen_seed") == r for j, r in one_right); nl = sum(not j.get("letter") for j, _ in one_right)
    print(f"within-pair (one right, one wrong; {len(one_right)} pairs): judge picks the right one {w/max(1,len(one_right)):.2f}; no letter {nl}")
    L = [z for z in J.values() if not z.get("same")]
    print(f"position: picked the first shown {sum(z.get('letter') == 'A' for z in L)} / {len(L)}; judge tokens {sum(z['out_tokens'] for z in L)/max(1,len(L))/1000:.2f}k, calls {sum(z.get('calls', 0) for z in L)/max(1,len(L)):.1f}")


if __name__ == "__main__":
    {"run": run, "score": score}[sys.argv[1]]()
