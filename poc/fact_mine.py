"""FM (docs/prereg/PREREG_FM.md): execution-verified fact mining for solver code on the Solomon VRPTW set.
mine: rounds of (programs on the 8 mining instances x 2 seeds with the current sheet -> failure reports -> 2 candidate facts from the
      model -> each candidate re-run with the same seeds -> keep the better one if it adds >= 2 feasible programs). Up to 5 rounds.
      -> results/h3/fm_chain_<chain>.json (verified sheet, every proposed fact, counts, tokens)
test: the 48 other instances with a sheet (verified | unverified) -> results/h3/sol_fm_<chain>_<which>[_on_<tag>]_s<seed>.jsonl
usage: POC_BASE_URL=... POC_REASONING_EFFORT=low python fact_mine.py mine <chain> [--v2] [--max_tokens N]   (FM2: --v2, chains C / D)
       POC_BASE_URL=... POC_REASONING_EFFORT=low python fact_mine.py pool <name> <chains ...> [--max_tokens N]   (FM3)
       POC_BASE_URL=... POC_REASONING_EFFORT=low python fact_mine.py test <chain> <verified|unverified> <seed> [<model_tag>] [--max_tokens N]"""
import json, os, re, sys, zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_solomon import RES, STATEMENT, TLIM, check, load, names  # noqa: E402
from sandbox import run_python  # noqa: E402

MINE = ["c101", "c201", "r101", "r201", "rc101", "rc201", "r105", "rc105"]
ROUNDS, NCAND, MIN_GAIN = 5, 2, 2
MAXTOK = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 6000


def prompt(name, sheet):
    inp = open(f"{RES}/instances/{name}.txt").read().replace("\r\n", "\n")
    p = STATEMENT.replace("{T}", str(TLIM))
    p += ("\n\nThe first 12 lines of this instance's input, verbatim (header lines, blank lines, then one row per customer):\n```\n"
          + "\n".join(inp.split("\n")[:12]) + "\n```")
    if sheet:
        p += "\n\nFacts learned from earlier runs on other instances of this task (follow them):\n" + "\n".join(f"- {f}" for f in sheet)
    return p


def attempt(name, seed, sheet, salt=5000):
    """One program for one instance: generation, run, check, failure report."""
    o = chat(prompt(name, sheet), max_tokens=MAXTOK, temperature=0.7, seed=salt + seed * 1000 + zlib.crc32(name.encode()) % 997)
    code = last_block(o["text"] or "", ("python", "py", "python3"))
    row = {"name": name, "seed": seed, "out_tokens": o.get("out_tokens") or 0, "code": code}
    if not code:
        return {**row, "feasible": False, "reason": "no code", "report": "The reply contained no complete program.", "distance": None}
    inp = open(f"{RES}/instances/{name}.txt").read().replace("\r\n", "\n")
    r = run_python(code, inp, timeout=TLIM + 30, mem_bytes=4 << 30)
    if r.status != "ok":
        tb = (r.stderr or "").strip().split("\n")
        rep = "\n".join(tb[-6:])[-1200:]
        m = [int(x) for x in re.findall(r'main\.py", line (\d+)', r.stderr or "")]
        if m:
            lines = code.split("\n"); ln = m[-1]
            rep += "\nCode around the failing line:\n" + "\n".join(lines[max(0, ln - 4): ln + 1])
        if r.status == "tle":
            rep = f"The program did not finish within {TLIM + 30} seconds."
        return {**row, "feasible": False, "reason": r.status, "report": rep, "distance": None}
    ok, dist, veh, why, detail = check(load(name), r.stdout, detail=True)
    return {**row, "feasible": ok, "reason": why, "report": "" if ok else "Infeasible output: " + detail, "distance": dist}


def run_set(insts, sheet, workers=8, salt=5000):
    jobs = [(n, s) for n in insts for s in (1, 2)]
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda a: attempt(a[0], a[1], sheet, salt), jobs))


ASK = """Programs written by a language model for the following task keep failing. Your job is to write ONE short fact that, added to the
task description, would prevent the most common failure below for every instance of this task.

TASK (as given to the model):
{task}

Facts already given to the model:
{sheet}

Failure reports from different instances:
{reports}

Write ONE new fact: one or two sentences about the input format, the library API, or the algorithm, true for every instance of this task,
with no numbers specific to one instance and no complete program (a short code expression is fine). Reply with the fact only, inside a
```fact block."""


ASK2 = ASK.replace("""Write ONE new fact: one or two sentences about the input format, the library API, or the algorithm, true for every instance of this task,
with no numbers specific to one instance and no complete program (a short code expression is fine). Reply with the fact only, inside a
```fact block.""", """The most common failure right now is: {target}
Write ONE new fact that fixes it: either one or two sentences, or a short code snippet of at most 15 lines (for example a helper function
the program can copy), about the input format, the library API, or the algorithm. It must be true for every instance of this task, with no
numbers specific to one instance and no complete program. Reply with the fact only, inside a ```fact block.""")
V2 = "--v2" in sys.argv


def sig(r):
    """Failure signature: None if feasible; the violated constraint class; or the last error line with literals masked."""
    if r["feasible"]:
        return None
    if r["reason"] in ("no code", "tle"):
        return r["reason"]
    if r["reason"] not in ("re", "mle"):
        return "infeasible: " + r["reason"]
    lines = [x for x in r["report"].split("Code around")[0].strip().split("\n") if x.strip()]
    err = [x for x in lines if re.match(r"^\s*[\w.]*(Error|Exception)\b", x)]
    s = (err[-1] if err else (lines[-1] if lines else "crash")).strip()[:160]
    return re.sub(r"'[^']*'", "'…'", re.sub(r"\b\d+(\.\d+)?\b", "N", s))


def propose(rows, sheet, rnd, chain, target=None):
    fails = [r for r in rows if not r["feasible"]]
    seen, picked = set(), []
    for r in fails:   # diverse reports: distinct last lines first
        key = (r["report"].strip().split("\n") or [""])[0][-80:]
        if key not in seen:
            seen.add(key); picked.append(r)
    picked = (picked + [r for r in fails if r not in picked])[:6]
    if target is not None:   # FM2: reports of the targeted failure first
        tg = [r for r in fails if sig(r) == target][:4]
        picked = tg + [r for r in picked if r not in tg][:6 - len(tg)]
    reports = "\n\n".join(f"[{r['name']}] {r['report']}" for r in picked)
    task = prompt("c101", []).split("\n\nThe first 12 lines")[0]
    out, tok = [], 0
    for i in range(NCAND):
        q = (ASK2.replace("{target}", target.replace("{", "{{").replace("}", "}}")) if target is not None else ASK).format(
            task=task, sheet="\n".join(f"- {f}" for f in sheet) or "(none)", reports=reports)
        o = chat(q, max_tokens=MAXTOK,
                 temperature=0.7, seed=777 + 100 * rnd + i + (0 if chain in ("A", "C") else 50000 if chain in ("B", "D") else 100000 * (ord(chain) - ord("D"))))
        tok += o.get("out_tokens") or 0
        f = last_block(o["text"] or "", ("fact",)) or (o["text"] or "").strip().split("\n")[-1]
        f = f.strip()[:1500] if V2 else " ".join(f.split())[:600]   # FM2 keeps code layout
        if f:
            out.append(f)
    return out, tok


def mine(chain):
    salt = 5000 if chain in ("A", "C") else 15000 if chain in ("B", "D") else 25000 + 10000 * (ord(chain) - ord("E"))
    sheet, proposed, log, tok = [], [], [], 0
    rows = run_set(MINE, sheet, salt=salt); tok += sum(r["out_tokens"] for r in rows)
    base = sum(r["feasible"] for r in rows)
    log.append({"round": 0, "sheet": [], "feasible": base, "reasons": [r["reason"] for r in rows]})
    print(chain, "round 0: feasible", base, "of 16", flush=True)
    for rnd in range(1, ROUNDS + 1):
        if base == 16:
            break
        target = Counter(sig(r) for r in rows if not r["feasible"]).most_common(1)[0][0] if V2 else None
        cands, t = propose(rows, sheet, rnd, chain, target); tok += t; proposed += cands
        res = []
        for c in cands:
            rr = run_set(MINE, sheet + [c], salt=salt); tok += sum(r["out_tokens"] for r in rr)
            res.append((sum(r["feasible"] for r in rr), c, rr))
        if V2:   # FM2: the targeted failure must drop by half, feasibility must not drop by more than 1
            t0 = sum(sig(r) == target for r in rows)
            ok_ = [x for x in res if sum(sig(r) == target for r in x[2]) <= t0 / 2 and x[0] >= base - 1]
            best = max(ok_, key=lambda x: (x[0], -sum(sig(r) == target for r in x[2]))) if ok_ else None
            kept = best is not None
            log_extra = {"target": target, "target_before": t0, "target_after": [sum(sig(r) == target for r in x[2]) for x in res]}
        else:
            best = max(res, key=lambda x: x[0]) if res else None
            kept = best is not None and best[0] >= base + MIN_GAIN
            log_extra = {}
        if kept:
            sheet = sheet + [best[1]]; base, rows = best[0], best[2]
        log.append({"round": rnd, "candidates": [(n, c) for n, c, _ in res], "kept": best[1] if kept else None, "feasible": base, **log_extra})
        print(chain, f"round {rnd}: candidates {[n for n, _, _ in res]} (base before {log[-2]['feasible']}) {log_extra} -> kept: {kept}", flush=True)
    json.dump({"chain": chain, "verified": sheet, "unverified": proposed, "log": log, "mining_tokens": tok}, open(f"{RES}/fm_chain_{chain}.json", "w"), indent=1)
    print(chain, "final sheet:", json.dumps(sheet, indent=1), "\nmining tokens", tok)


def pool(name, chains):
    """FM3: pool the verified facts of several chains; one pass of backward elimination on the mining set (fixed random order)."""
    import random
    facts = [f for c in chains for f in json.load(open(f"{RES}/fm_chain_{c}.json"))["verified"]]
    tok = 0
    rows = run_set(MINE, facts, salt=5000); tok += sum(r["out_tokens"] for r in rows)
    base = sum(r["feasible"] for r in rows); log = [{"pool": len(facts), "feasible": base}]
    print(name, f"pool of {len(facts)} facts: feasible {base} of 16", flush=True)
    order = list(range(len(facts))); random.Random(0).shuffle(order)
    keep = set(range(len(facts)))
    for i in order:
        trial = [facts[j] for j in sorted(keep - {i})]
        rr = run_set(MINE, trial, salt=5000); tok += sum(r["out_tokens"] for r in rr)
        f = sum(r["feasible"] for r in rr)
        dropped = f >= base
        if dropped:
            keep.discard(i); base = f
        log.append({"fact": i, "without": f, "dropped": dropped, "feasible": base})
        print(name, f"without fact {i}: {f} -> {'drop' if dropped else 'keep'} (now {len(keep)} facts, base {base})", flush=True)
    sheet = [facts[j] for j in sorted(keep)]
    prior = sum(json.load(open(f"{RES}/fm_chain_{c}.json"))["mining_tokens"] for c in chains)
    json.dump({"chain": name, "verified": sheet, "unverified": facts, "log": log, "mining_tokens": tok, "chain_tokens": prior},
              open(f"{RES}/fm_chain_{name}.json", "w"), indent=1)
    print(name, "pruned sheet:", json.dumps(sheet, indent=1), "\npool + pruning tokens", tok, "+ chains", prior)


def test(chain, which, seed, model_tag):
    C = json.load(open(f"{RES}/fm_chain_{chain}.json"))
    sheet = C[which]
    insts = [n for n in names() if n not in MINE]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda n: attempt(n, seed, sheet, salt=0), insts))
    tag = f"fm_{chain}_{which}" + (f"_on_{model_tag}" if model_tag else "")
    with open(f"{RES}/sol_{tag}_s{seed}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(tag, seed, f"feasible {sum(r['feasible'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    if sys.argv[1] == "mine":
        mine(sys.argv[2])
    elif sys.argv[1] == "pool":   # python fact_mine.py pool <name> <chain> <chain> ...
        pool(sys.argv[2], [c for c in sys.argv[3:] if not c.startswith("--") and not c.isdigit()])
    else:
        test(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].startswith("--") else "")
