"""X4 (docs/prereg/PREREG_X3.md, X4 section): whole-proof generation for miniF2F (Lean 4 v4.15.0 + Mathlib v4.15.0 in /SSD/lean_postech/mf2f).
The file checked is the dataset header + the dataset's formal statement (never the model's) + the model's proof body (the text after
the first ':= by' of the model's Lean block). Accepted = compiles with no error, no `sorry` / `admit` / `axiom`.
usage: POC_BASE_URL=... python run_lean.py gen <tag> <split> <k> [--logprobs] [--max_tokens N] [--think] [--card_prompt] [--exemplar <tag>]  -> results/x4/lean_<tag>_<split>.jsonl
       python run_lean.py check <file.jsonl>          (compile every attempt; adds ok / errors / unknown identifiers)
       POC_BASE_URL=... python run_lean.py fix <tag> <split>   (one feedback round for proofs whose errors name unknown identifiers)"""
import json, os, re, subprocess, sys, tempfile, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OUT = f"{RES}/x4"
PROJ = "/SSD/lean_postech/mf2f"
ENV = {**os.environ, "ELAN_HOME": "/SSD/lean_postech/elan", "PATH": "/SSD/lean_postech/elan/bin:" + os.environ.get("PATH", "")}
PROMPT = ("Complete the following Lean 4 theorem (Mathlib is imported). Think about the mathematics briefly, then give the complete theorem "
          "with its proof in a single ```lean4 code block. Do not use `sorry`.\n\n```lean4\n{header}\n{stmt}\n```")
# the prompt both specialized provers' model cards use (Goedel-Prover-V2, DeepSeek-Prover-V2); used with --card_prompt (2026-10-17)
CARD_PROMPT = ("Complete the following Lean 4 code:\n\n```lean4\n{header}\n{stmt}\n```\n\nBefore producing the Lean 4 code to formally prove the "
               "given theorem, provide a detailed proof plan outlining the main proof steps and strategies.\nThe plan should highlight key ideas, "
               "intermediate lemmas, and proof structures that will guide the construction of the final formal proof.")



def _rows(path):
    """rows of a results file; skips a torn line (a NUL-filled line from an interrupted write on the NAS, 2026-10-18)"""
    out = []
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out

def problems(split):
    M = json.load(open(f"{RES}/x3/minif2f.json"))
    return [m for m in M if m["split"] == split]


def proof_body(text):
    blocks = re.findall(r"```(?:lean4|lean)?[ \t]*\n(.*?)```", text or "", re.S)
    if not blocks:
        return None
    b = blocks[-1]
    m = re.search(r":=\s*by\b", b)   # ':= by', also ':=\n  by' (2026-10-18: Qwen3-14B writes the line break; 'no proof' was a harness miss)
    if m:
        return b[m.end():]
    t = b.lstrip()   # a block that is only the proof ("by\n  tactics"): 26 of 1,952 gpt-oss attempts (fixed 20:30)
    return "\n" + t[2:] if t.startswith("by") and (len(t) == 2 or t[2] in " \n") else None


def check(header, stmt, body, timeout=180):
    if body is None:
        return {"ok": False, "errors": ["no proof"], "unknown": []}
    if re.search(r"\b(sorry|admit)\b|^\s*axiom\b", body, re.M):
        return {"ok": False, "errors": ["sorry/admit"], "unknown": []}
    src = header + "\n" + stmt + body + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".lean", dir="/SSD/lean_postech/tmp", delete=False) as f:
        f.write(src); path = f.name
    try:
        p = subprocess.Popen(["lake", "env", "lean", path], cwd=PROJ, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             start_new_session=True)   # own process group: on timeout kill lake AND lean (orphans ran for 5 h, 2026-10-17)
        try:
            so, se = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9); p.communicate()
            raise
        r = subprocess.CompletedProcess(p.args, p.returncode, so, se)
        out = (r.stdout or "") + (r.stderr or "")
        errs = [l for l in out.splitlines() if ": error:" in l]
        unknown = sorted(set(re.findall(r"unknown (?:identifier|constant) '([^']+)'", out)))
        return {"ok": r.returncode == 0 and not errs, "errors": errs[:5], "unknown": unknown}
    except subprocess.TimeoutExpired:
        return {"ok": False, "errors": ["timeout"], "unknown": []}
    finally:
        os.unlink(path)


def exemplars(src_tag, split):
    """phase 2 (facts first for proofs): for each statement, the most similar OTHER statement (BM25 over statement tokens) that
    <src_tag> proved, with its verified proof"""
    import math
    from collections import Counter
    rows = [r for r in _rows(f"{OUT}/lean_{src_tag}_{split}.jsonl") if r.get("ok")]
    best = {}
    for r in rows:
        best.setdefault(r["name"], r)   # one verified proof per statement
    M = {m["name"]: m for m in problems(split)}
    tok = lambda t: re.findall(r"[A-Za-z_][A-Za-z_0-9.]*|\d+|[^\sA-Za-z_0-9]", t)
    docs = {n: Counter(tok(M[n]["formal_statement"])) for n in best if n in M}
    df = Counter(w for d in docs.values() for w in d); N = max(1, len(docs)); avg = sum(sum(d.values()) for d in docs.values()) / N
    def score(q, d):
        L = sum(d.values())
        return sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * d[w] * 2.2 / (d[w] + 1.2 * (.25 + .75 * L / avg)) for w in q if w in d)
    out = {}
    for n, m in M.items():
        q = set(tok(m["formal_statement"]))
        cands = [(score(q, d), o) for o, d in docs.items() if o != n]
        if cands:
            o = max(cands)[1]
            out[n] = (M[o]["formal_statement"] + best[o]["body"]).strip()
    return out


def gen(tag, split, k, logprobs, mt, think=False, card=False, ex_tag=""):
    from llm import chat
    from concurrent.futures import as_completed
    P = problems(split)
    if os.environ.get("LEAN_ONLY"):   # a file with one statement name per line (e.g. the ones still unsolved after 8 attempts)
        keep = set(open(os.environ["LEAN_ONLY"]).read().split()); P = [p for p in P if p["name"] in keep]
    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/lean_{tag}_{split}.jsonl"   # rows flushed as they finish; a re-run resumes (2026-10-17)
    done = {(r["name"], r["sample"]) for r in _rows(path)}
    jobs = [(p, s) for p in P for s in range(1, k + 1) if (p["name"], s) not in done]
    EX = exemplars(ex_tag, split) if ex_tag else {}

    def one(j):
        p, s = j
        q = (CARD_PROMPT if card else PROMPT).format(header=p["header"].strip(), stmt=p["formal_statement"])
        if p["name"] in EX:   # phase 2: a verified proof of the most similar other statement, before the task
            q = ("Here is a similar theorem with a proof that Lean 4 + Mathlib accepts:\n```lean4\n" + EX[p["name"]] + "\n```\n\n" + q)
        o = chat(q, temperature=0.7, max_tokens=mt, think=think,
                 seed=s * 1000 + zlib.crc32(p["name"].encode()) % 997, logprobs=logprobs)
        return {"name": p["name"], "sample": s, "text": (o["text"] or "")[-6000:], "body": proof_body(o["text"]),
                "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), **({"lp": o.get("lp"), "lp_tok": o.get("lp_tok")} if logprobs else {})}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, j) for j in jobs]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(tag, split, "generated", sum(1 for _ in open(path)), flush=True)


def check_file(path):
    M = {m["name"]: m for m in json.load(open(f"{RES}/x3/minif2f.json"))}
    rows = [json.loads(l) for l in open(path)]
    os.makedirs("/SSD/lean_postech/tmp", exist_ok=True)
    todo = [r for r in rows if "ok" not in r]   # rows checked before keep their result (2026-10-18: extra attempts appended later)
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(lambda r: check(M[r["name"]]["header"], M[r["name"]]["formal_statement"], r.get("body")), todo))
    for r, c in zip(todo, res):
        r.update(c)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    solved = {r["name"] for r in rows if r["ok"]}
    print(path, f"attempts ok {sum(r['ok'] for r in rows)}/{len(rows)}, statements solved {len(solved)}/{len({r['name'] for r in rows})}, "
          f"attempts naming unknown identifiers {sum(bool(r['unknown']) for r in rows)}", flush=True)


def recheck_missing(path):
    """re-extract the proof body where the first extractor found none, and check only those attempts"""
    M = {m["name"]: m for m in json.load(open(f"{RES}/x3/minif2f.json"))}
    rows = [json.loads(l) for l in open(path)]
    todo = [r for r in rows if r.get("body") is None and proof_body(r["text"]) is not None]
    for r in todo:
        r["body"] = proof_body(r["text"])
    os.makedirs("/SSD/lean_postech/tmp", exist_ok=True)
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(lambda r: check(M[r["name"]]["header"], M[r["name"]]["formal_statement"], r["body"]), todo))
    for r, c in zip(todo, res):
        r.update(c)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(path, f"re-extracted {len(todo)}, of which ok {sum(c['ok'] for c in res)}; now attempts ok {sum(r['ok'] for r in rows)}/{len(rows)}, "
          f"statements solved {len({r['name'] for r in rows if r['ok']})}", flush=True)


def fix(tag, split):
    """X4-P2: for every attempt whose errors name unknown identifiers: (a) one feedback round naming them, (b) a fresh sample
    (new seed); both are then checked (results/x4/fix_<tag>_<split>.jsonl)"""
    from llm import chat
    M = {m["name"]: m for m in json.load(open(f"{RES}/x3/minif2f.json"))}
    rows = [r for r in map(json.loads, open(f"{OUT}/lean_{tag}_{split}.jsonl")) if r.get("unknown") and not r["ok"]]

    def one(r):
        p = M[r["name"]]; base = PROMPT.format(header=p["header"].strip(), stmt=p["formal_statement"])
        names = ", ".join(f"`{u}`" for u in r["unknown"])
        fb = (base + f"\n\nA previous attempt used these names, which do NOT exist in Mathlib: {names}. Here is that attempt:\n```lean4\n"
              f"{p['formal_statement']}{r['body']}\n```\nWrite a corrected complete proof that does not use those names, in a single ```lean4 block.")
        sd = 100 + r["sample"] * 1000 + zlib.crc32(r["name"].encode()) % 997
        a = chat(fb, temperature=0.7, max_tokens=16000, seed=sd)
        b = chat(base, temperature=0.7, max_tokens=16000, seed=sd + 7)
        ca = check(p["header"], p["formal_statement"], proof_body(a["text"]))
        cb = check(p["header"], p["formal_statement"], proof_body(b["text"]))
        return {"name": r["name"], "sample": r["sample"], "unknown": r["unknown"], "fix_ok": ca["ok"], "fix_unknown": ca["unknown"],
                "fix_tokens": a.get("out_tokens"), "fresh_ok": cb["ok"], "fresh_unknown": cb["unknown"], "fresh_tokens": b.get("out_tokens"),
                "fix_text": (a["text"] or "")[-3000:], "fresh_text": (b["text"] or "")[-3000:]}
    os.makedirs("/SSD/lean_postech/tmp", exist_ok=True)
    with ThreadPoolExecutor(24) as ex:
        out = list(ex.map(one, rows))
    with open(f"{OUT}/fix_{tag}_{split}.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    n = len(out)
    print(f"{tag}: {n} attempts with unknown names; feedback round ok {sum(r['fix_ok'] for r in out)} ({sum(r['fix_tokens'] or 0 for r in out) / max(1, n):.0f} tokens), "
          f"fresh sample ok {sum(r['fresh_ok'] for r in out)} ({sum(r['fresh_tokens'] or 0 for r in out) / max(1, n):.0f} tokens); still naming unknown "
          f"identifiers: fix {sum(bool(r['fix_unknown']) for r in out)}, fresh {sum(bool(r['fresh_unknown']) for r in out)}", flush=True)


def revise(tag, split, mt=32000):
    """PROOF-R (docs/prereg/PREREG_PROOF.md): for statements whose FIRST attempt failed, one revision from the compiler's errors
    (self-correction) vs the fresh second attempt already stored; card prompt + thinking (provers). -> results/x4/revise_<tag>_<split>.jsonl"""
    from llm import chat
    from concurrent.futures import as_completed
    M = {m["name"]: m for m in problems(split)}
    first = {r["name"]: r for r in _rows(f"{OUT}/lean_{tag}_{split}.jsonl") if r["sample"] == 1 and "ok" in r and not r["ok"]}
    path = f"{OUT}/revise_{tag}_{split}.jsonl"
    done = {r["name"] for r in _rows(path)}
    os.makedirs("/SSD/lean_postech/tmp", exist_ok=True)

    def one(r):
        p = M[r["name"]]
        prev = (p["formal_statement"] + (r.get("body") or "\n  sorry")).strip()
        errs = "\n".join(r.get("errors") or ["(no proof was produced)"])
        q = (CARD_PROMPT.format(header=p["header"].strip(), stmt=p["formal_statement"]) + "\n\nA previous attempt:\n```lean4\n" + prev +
             "\n```\nLean 4 reports:\n" + errs + "\nRevise the proof so that it compiles. Give the complete theorem in a single ```lean4 block.")
        o = chat(q, temperature=0.7, max_tokens=mt, think=True, seed=7000 + zlib.crc32(r["name"].encode()) % 997)
        body = proof_body(o["text"]); c = check(p["header"], p["formal_statement"], body)
        return {"name": r["name"], "ok": c["ok"], "errors": c["errors"], "unknown": c["unknown"], "out_tokens": o.get("out_tokens"),
                "finish": o.get("finish"), "body": body, "text": (o["text"] or "")[-3000:]}
    with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, r) for n, r in first.items() if n not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    print(tag, "revised", sum(1 for _ in open(path)), "first-attempt failures", flush=True)


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "gen":
        gen(a[2], a[3], int(a[4]), "--logprobs" in a, int(a[a.index("--max_tokens") + 1]) if "--max_tokens" in a else 8192, "--think" in a, "--card_prompt" in a,
            a[a.index("--exemplar") + 1] if "--exemplar" in a else "")
    elif a[1] == "check":
        check_file(a[2])
    elif a[1] == "recheck":
        recheck_missing(a[2])
    elif a[1] == "revise":
        revise(a[2], a[3])
    elif a[1] == "fix":
        fix(a[2], a[3])
