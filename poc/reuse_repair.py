"""V2 (results/PREREG_V.md): repair one program on the 8 mining instances (up to 3 rounds), then reuse it on the 48 test instances.
usage: POC_BASE_URL=... [POC_REASONING_EFFORT=low] python reuse_repair.py <arm> [--max_tokens N] [--think] [--guard (V3)]
       -> results/h3/reuse_v2_<arm>.json"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_solomon import RES, STATEMENT, TLIM, check, load, names  # noqa: E402
from sandbox import run_python  # noqa: E402

MINE = ["c101", "c201", "r101", "r201", "rc101", "rc201", "r105", "rc105"]
TEST = [n for n in names() if n not in MINE]
B = json.load(open(f"{RES}/bks.json")); R0 = json.load(open(f"{RES}/ref.json"))["ortools300_ins"]
REF = {n: min(B[n]["distance"], R0[n]["distance"]) for n in B}
MAXTOK = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 6000
THINK = "--think" in sys.argv


def run1(code, n):
    inp = open(f"{RES}/instances/{n}.txt").read().replace("\r\n", "\n")
    r = run_python(code, inp, timeout=TLIM + 30, mem_bytes=4 << 30)
    if r.status != "ok":
        msg = ("did not finish within the time limit" if r.status == "tle" else
               "crashed:\n" + "\n".join((r.stderr or "").strip().split("\n")[-8:])[-1200:])
        return {"feasible": False, "crash": True, "msg": msg, "distance": None}
    if not r.stdout.strip():   # name an empty output as such (2026-10-14: "customers missing [1..30]" hid it)
        return {"feasible": False, "crash": False, "msg": "printed nothing (no solution was output; maybe the solver found none)", "distance": None}
    ok, dist, veh, why, detail = check(load(n), r.stdout, detail=True)
    return {"feasible": ok, "crash": False, "msg": "" if ok else "printed an infeasible solution: " + detail, "distance": dist}


def evaluate(code, insts):
    with ThreadPoolExecutor(12) as ex:
        return dict(zip(insts, ex.map(lambda n: run1(code, n), insts)))


GUARD = "--guard" in sys.argv   # V3: a repaired program must beat our greedy baseline by >= 10% on the mining instances it solves


def greedy_dist():
    from run_solomon import REF_GREEDY
    return {n: v["distance"] for n, v in evaluate(REF_GREEDY, MINE).items()}


def passes_guard(ev, gd):
    s = [(v["distance"], gd[n]) for n, v in ev.items() if v["feasible"] and gd.get(n)]
    return bool(s) and sum(a for a, _ in s) <= 0.9 * sum(b for _, b in s)


def main(arm):
    cands = [r for sd in (1, 2) for r in map(json.loads, open(f"{RES}/sol_{arm}_s{sd}.jsonl")) if r["name"] in MINE and r.get("code")]
    gen_tok = sum(c.get("out_tokens") or 0 for c in cands)
    with ThreadPoolExecutor(2) as ex:
        evs = list(ex.map(lambda c: evaluate(c["code"], MINE), cands))
    key = lambda e: (sum(v["feasible"] for v in e.values()), -sum(v["crash"] for v in e.values()))
    i = max(range(len(cands)), key=lambda k: key(evs[k]))
    code, ev = cands[i]["code"], evs[i]
    global GD
    GD = greedy_dist() if GUARD else {}
    if GUARD and key(ev)[0] and not passes_guard(ev, GD):   # the starting program itself must pass the guard
        ev = {n: {**v, "feasible": False, "msg": "solutions are no better than a simple greedy heuristic"} for n, v in ev.items()}
    log = [{"round": 0, "mining_feasible": key(ev)[0], "crashes": -key(ev)[1]}]
    print(arm, "round 0:", log[-1], flush=True)
    rep_tok = 0
    head = "\n".join(open(f"{RES}/instances/c101.txt").read().replace("\r\n", "\n").split("\n")[:12])
    for rnd in range(1, 4):
        if key(ev)[0] == len(MINE):
            break
        fails = [(n, v["msg"]) for n, v in ev.items() if not v["feasible"]][:4]
        prompt = (STATEMENT.replace("{T}", str(TLIM)) + "\n\nThe first 12 lines of one instance's input, verbatim:\n```\n" + head + "\n```"
                  + f"\n\nYour previous program:\n```python\n{code}\n```\n\nIt fails on these benchmark instances (same format, different data):\n"
                  + "\n".join(f"- {n}: {m}" for n, m in fails)
                  + "\n\nFix the program so that it works on every instance of this benchmark. Give the complete corrected program in a single ```python code block.")
        o = chat(prompt, think=THINK, max_tokens=MAXTOK, temperature=0.7, seed=4000 + rnd + zlib.crc32(arm.encode()) % 997)
        rep_tok += o.get("out_tokens") or 0
        new = last_block(o["text"] or "", ("python", "py", "python3"))
        if not new:
            log.append({"round": rnd, "accepted": False, "why": "no code"}); continue
        ev2 = evaluate(new, MINE)
        acc = key(ev2)[0] > key(ev)[0] and (not GUARD or passes_guard(ev2, GD))
        log.append({"round": rnd, "candidate_feasible": key(ev2)[0], "accepted": acc})
        print(arm, f"round {rnd}: candidate feasible on {key(ev2)[0]} / 8 -> {'accept' if acc else 'reject'}", flush=True)
        if acc:
            code, ev = new, ev2
    res = evaluate(code, TEST) if key(ev)[0] else {}
    g = sorted(100 * (v["distance"] / REF[n] - 1) for n, v in res.items() if v["feasible"])
    out = {"arm": arm, "log": log, "mining_feasible": key(ev)[0], "test_feasible": len(g), "median_gap": g[len(g) // 2] if g else None,
           "within5": sum(x <= 5 for x in g), "gen_tokens": gen_tok, "repair_tokens": rep_tok, "code": code}
    json.dump(out, open(f"{RES}/reuse_v2_{arm}{os.environ.get('V2_SUFFIX', '')}.json", "w"), indent=1)
    print(arm, f"final: mining {key(ev)[0]}/8, test {len(g)}/48 ({100 * len(g) / 48:.0f}%), median gap {out['median_gap']}, "
          f"tokens {gen_tok} + {rep_tok}")


if __name__ == "__main__":
    main(sys.argv[1])
