"""X4-P2b (PREREG_X3.md): feedback that names the 3 most similar EXISTING Mathlib names (with their types) for each non-existent name.
usage: POC_BASE_URL=... python lean_factfix.py <tag> <split>  -> results/x4/factfix_<tag>_<split>.jsonl"""
import difflib, json, os, re, subprocess, sys, tempfile, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_lean as L  # noqa: E402
from llm import chat  # noqa: E402
_DATA = os.environ.get("POC_DATA", "/NAS/SJ/POSTECH/nlp_data")   # Slurm server (2026-10-22): external data; old server: /SSD/lean_postech

NAMES = open(_DATA + "/mathlib_names.txt").read().split("\n")
BY_PART = {}
for n in NAMES:
    for p in set(re.split(r"[._]", n.split(".")[-1].lower())):
        if len(p) > 2:
            BY_PART.setdefault(p, []).append(n)


def nearest(u, k=3):
    parts = {p for p in re.split(r"[._]", u.split(".")[-1].lower()) if len(p) > 2}
    pool = set()
    for p in parts:
        pool.update(BY_PART.get(p, [])[:20000])
    return difflib.get_close_matches(u, list(pool), n=k, cutoff=0.5)


def types(names):
    if not names:
        return {}
    src = "import Mathlib\n" + "\n".join(f"#check @{n}" for n in names) + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=_DATA + "/tmp", delete=False) as f:
        f.write(src); path = f.name
    try:
        r = subprocess.run(["lake", "env", "lean", path], cwd=L.PROJ, env=L.ENV, capture_output=True, text=True, timeout=180)
        out = r.stdout + r.stderr
    finally:
        os.unlink(path)
    res = {}
    for n in names:
        m = re.search(r"(?m)^@?" + re.escape(n) + r" : (.*?)(?=\n\S|\Z)", out, re.S)
        if m:
            res[n] = " ".join(m.group(1).split())[:300]
    return res


def main(tag, split):
    M = {m["name"]: m for m in json.load(open(f"{L.RES}/x3/minif2f.json"))}
    rows = [r for r in map(json.loads, open(f"{L.OUT}/lean_{tag}_{split}.jsonl")) if r.get("unknown") and not r["ok"]]

    def one(r):
        p = M[r["name"]]; base = L.PROMPT.format(header=p["header"].strip(), stmt=p["formal_statement"])
        sugg = {u: nearest(u) for u in r["unknown"]}
        ty = types(sorted({s for v in sugg.values() for s in v}))
        facts = "\n".join(f"- `{u}` does not exist. Existing Mathlib names that are similar: " +
                          ("; ".join(f"`{s} : {ty[s]}`" if s in ty else f"`{s}`" for s in v) if v else "(none found)") for u, v in sugg.items())
        prompt = (base + f"\n\nA previous attempt used names that do NOT exist in Mathlib. Facts:\n{facts}\nHere is that attempt:\n```lean4\n"
                  f"{p['formal_statement']}{r['body']}\n```\nWrite a corrected complete proof (use existing lemmas only) in a single ```lean4 block.")
        sd = 100 + r["sample"] * 1000 + zlib.crc32(r["name"].encode()) % 997
        a = chat(prompt, temperature=0.7, max_tokens=16000, seed=sd)
        ca = L.check(p["header"], p["formal_statement"], L.proof_body(a["text"]))
        return {"name": r["name"], "sample": r["sample"], "unknown": r["unknown"], "suggestions": sugg, "types_found": len(ty),
                "ok": ca["ok"], "still_unknown": ca["unknown"], "tokens": a.get("out_tokens"), "text": (a["text"] or "")[-3000:]}
    os.makedirs(_DATA + "/tmp", exist_ok=True)
    with ThreadPoolExecutor(16) as ex:
        out = list(ex.map(one, rows))
    with open(f"{L.OUT}/factfix_{tag}_{split}.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    n = len(out)
    print(f"{tag}: {n} attempts; feedback with similar existing names ok {sum(r['ok'] for r in out)} ({sum(r['tokens'] or 0 for r in out) / max(1, n):.0f} tokens); "
          f"still naming unknown identifiers {sum(bool(r['still_unknown']) for r in out)}; suggestions found for "
          f"{sum(all(r['suggestions'][u] for u in r['unknown']) for r in out)} / {n}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
