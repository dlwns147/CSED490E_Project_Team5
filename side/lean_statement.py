"""SIDE-PF, the Lean arm (docs/prereg/PREREG_SIDE.md): test a natural-language statement in Lean before any proof. A model translates the
statement into a Lean 4 + Mathlib theorem (`gen`); Lean then searches for a counterexample with Plausible's random testing (`check`:
the theorem's proof is replaced by `plausible`). A counterexample Plausible prints is a real counterexample to the formal statement, so on
a true statement a flag can only come from a translation that changed the claim. Statements over types Plausible cannot sample (ℝ)
are reported as untestable. Messages as Lean v4.15 + Plausible print them (checked 11-04 on $POC_DATA/proof/leantest/T.lean): a
counterexample is an error "Found a counter-example!" with the instance; none found leaves only the warning "declaration uses 'sorry'";
an unsampleable type is "Failed to create a `testable` instance".
usage: $P side/lean_statement.py gen <tag> <ids file> [--think] [--max_tokens N]   (lane.sh job; POC_BASE_URL set)
         -> results/proof/ls_<tag>.jsonl (id, label, lean statement, tokens)
       python side/lean_statement.py check <tag> [batch]   (CPU job; Lean + Mathlib from run_lean.py's paths)
         -> results/proof/ls_<tag>_check.jsonl (id, label, status: counterexample / none found / untestable / ill-typed, message)"""
import json, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "poc"))
OUT = os.path.join(ROOT, "results", "proof")
DATA_ST = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "proof", "brokenmath", "bm.jsonl")
HEADER = "import Mathlib\nimport Plausible\n\nopen Real Nat Finset BigOperators\n\n"

PROMPT = """Translate the following competition statement into one Lean 4 theorem using Mathlib. Do not prove it.

Rules:
- State exactly the claim, with every hypothesis, and nothing more. Keep the number types the statement uses (ℕ, ℤ, ℚ, ℝ).
- If the statement asks to prove a value or a property of specific numbers, state that value or property directly.
- Name the theorem `stmt` and end it with `:= by sorry`.
- Reply with the theorem only, in one ```lean4 code block, without imports.

Statement:
{problem}"""


def lean_of(text):
    b = re.findall(r"```[a-zA-Z0-9]*[ \t]*\r?\n(.*?)```", text, flags=re.S)
    t = (b[-1] if b else text).strip()   # no code block: the theorem is searched in the whole reply
    t = "\n".join(l for l in t.splitlines() if not l.startswith(("import ", "open ", "set_option")))
    m = re.search(r"(theorem|lemma)\s+\S+", t)
    if m:
        return t[m.start():].strip()
    m = re.search(r"(?m)^\s*stmt\b", t)   # Qwen3-8B often writes `stmt : ...` without the keyword (dev, 11-04)
    return "theorem " + t[m.start():].strip() if m else None


def gen():
    from llm import chat
    tag, ids_file = sys.argv[2], sys.argv[3]
    think = "--think" in sys.argv
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else (12000 if think else 2048)
    want = set(open(ids_file).read().split())
    X = [x for x in map(json.loads, open(DATA_ST)) if x["id"] in want]
    os.makedirs(OUT, exist_ok=True)
    out = f"{OUT}/ls_{tag}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    todo = [x for x in X if x["id"] not in done]
    print(f"SIDE-PF Lean gen {tag}: {len(todo)} of {len(X)} statements (think={think})", flush=True)

    def one(x):
        r = chat(PROMPT.format(problem=x["problem"]), think=think, max_tokens=mt, temperature=0.6 if think else 0.7)
        return {"id": x["id"], "label": x["label"], "lean": lean_of(r["text"]), "out_tokens": r["out_tokens"], "finish": r["finish"],
                "text": r["text"][-2500:]}
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for k, fu in enumerate(as_completed([ex.submit(one, x) for x in todo])):
            try:
                r = fu.result()
            except Exception as e:
                print(f"  failed: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
            f.write(json.dumps(r) + "\n"); f.flush()


def to_plausible(stmt, name):
    """the theorem renamed, its proof replaced by Plausible's search"""
    s = re.sub(r"^(theorem|lemma)\s+\S+", f"theorem {name}", stmt.strip(), count=1)
    i = s.rfind(":=")
    return (s[:i] if i >= 0 else s).rstrip() + " := by\n  plausible\n"


def check():
    from run_lean import ENV, PROJ
    tag = sys.argv[2]
    batch = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    R = [json.loads(l) for l in open(f"{OUT}/ls_{tag}.jsonl")]
    for r in R:   # re-extract from the stored reply (the extractor may be newer than the rows)
        if r.get("text"):
            r["lean"] = lean_of(r["text"])
    out = f"{OUT}/ls_{tag}_check.jsonl"

    def run(rows):
        parts, spans, line = [HEADER], [], HEADER.count("\n") + 1
        for k, r in enumerate(rows):
            t = to_plausible(r["lean"], f"stmt_{k}") + "\n"
            spans.append((line, line + t.count("\n"))); parts.append(t); line += t.count("\n")
        with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=PROJ, delete=False) as fh:
            fh.write("".join(parts)); path = fh.name
        try:
            p = subprocess.run(["lake", "env", "lean", path], cwd=PROJ, env=ENV, capture_output=True, text=True, timeout=1800)
            msgs = p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            msgs = None
        finally:
            os.unlink(path)
        res = []
        blocks = re.split(r"(?m)^(?=\S+\.lean:\d+:\d+: )", msgs or "")
        for k, r in enumerate(rows):
            a, b = spans[k]
            mine = [m for m in blocks if (mm := re.match(r"\S+\.lean:(\d+):\d+: ", m)) and a <= int(mm.group(1)) < b]
            txt = "\n".join(mine)
            if msgs is None:
                st = "timeout"
            elif "Found a counter-example" in txt or "Found a counterexample" in txt:
                st = "counterexample"
            elif "Failed to create a `testable` instance" in txt or \
                    re.search(r"failed to synthesize\s+(Plausible\.)?(Testable|SampleableExt|Shrinkable|Decidable)", txt):
                st = "untestable"
            elif "Unable to find a counter-example" in txt or "Gave up" in txt or not re.search(r"\berror\b", txt):
                st = "none found"
            else:
                st = "ill-typed"
            res.append({"id": r["id"], "label": r["label"], "status": st, "flag": st == "counterexample", "msg": txt[:600]})
        return res

    rows = [r for r in R if r.get("lean")]
    miss = [{"id": r["id"], "label": r["label"], "status": "no statement", "flag": False, "msg": ""} for r in R if not r.get("lean")]
    chunks = [rows[i:i + batch] for i in range(0, len(rows), batch)]
    with ThreadPoolExecutor(int(os.environ.get("LEAN_WORKERS", 4))) as ex, open(out, "w") as f:
        for r in miss:
            f.write(json.dumps(r) + "\n")
        for fu in as_completed([ex.submit(run, c) for c in chunks]):
            for r in fu.result():
                f.write(json.dumps(r) + "\n")
            f.flush()
    print(f"SIDE-PF Lean check {tag}: {len(R)} statements -> {out}", flush=True)


if __name__ == "__main__":
    {"gen": gen, "check": check}[sys.argv[1]]()
