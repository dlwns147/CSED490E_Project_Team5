"""X4 (docs/prereg/PREREG_X3.md, X4 section): whole-proof generation for miniF2F (Lean 4 v4.15.0 + Mathlib v4.15.0 in /SSD/lean_postech/mf2f).
The file checked is the dataset header + the dataset's formal statement (never the model's) + the model's proof body (the text after
the first ':= by' of the model's Lean block). Accepted = compiles with no error, no `sorry` / `admit` / `axiom`.
usage: POC_BASE_URL=... python run_lean.py gen <tag> <split> <k> [--logprobs] [--max_tokens N]  -> results/x4/lean_<tag>_<split>.jsonl
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


def problems(split):
    M = json.load(open(f"{RES}/x3/minif2f.json"))
    return [m for m in M if m["split"] == split]


def proof_body(text):
    blocks = re.findall(r"```(?:lean4|lean)?[ \t]*\n(.*?)```", text or "", re.S)
    if not blocks:
        return None
    b = blocks[-1]
    i = b.find(":= by")
    if i >= 0:
        return b[i + len(":= by"):]
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


def gen(tag, split, k, logprobs, mt):
    from llm import chat
    P = problems(split)
    jobs = [(p, s) for p in P for s in range(1, k + 1)]

    def one(j):
        p, s = j
        o = chat(PROMPT.format(header=p["header"].strip(), stmt=p["formal_statement"]), temperature=0.7, max_tokens=mt,
                 seed=s * 1000 + zlib.crc32(p["name"].encode()) % 997, logprobs=logprobs)
        return {"name": p["name"], "sample": s, "text": (o["text"] or "")[-6000:], "body": proof_body(o["text"]),
                "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), **({"lp": o.get("lp"), "lp_tok": o.get("lp_tok")} if logprobs else {})}
    with ThreadPoolExecutor(48) as ex:
        rows = list(ex.map(one, jobs))
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/lean_{tag}_{split}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(tag, split, "generated", len(rows), flush=True)


def check_file(path):
    M = {m["name"]: m for m in json.load(open(f"{RES}/x3/minif2f.json"))}
    rows = [json.loads(l) for l in open(path)]
    os.makedirs("/SSD/lean_postech/tmp", exist_ok=True)
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(lambda r: check(M[r["name"]]["header"], M[r["name"]]["formal_statement"], r.get("body")), rows))
    for r, c in zip(rows, res):
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


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "gen":
        gen(a[2], a[3], int(a[4]), "--logprobs" in a, int(a[a.index("--max_tokens") + 1]) if "--max_tokens" in a else 8192)
    elif a[1] == "check":
        check_file(a[2])
    elif a[1] == "recheck":
        recheck_missing(a[2])
    elif a[1] == "fix":
        fix(a[2], a[3])
