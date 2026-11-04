"""SIDE-PF (docs/prereg/PREREG_SIDE.md): a free, partial check for natural-language proofs — look for a counterexample by computation.
A model reads a problem and a proposed proof and writes one Python program that (1) brute-forces the answer on small cases when the
problem asks to find or determine something, and compares it with the proof's claimed answer, and (2) tests the proof's concrete claims
(identities, inequalities, divisibility, claimed properties of small cases, geometric claims in coordinates) on small or random
instances that satisfy the stated hypotheses. The program runs in the sandbox (10 s) and prints `COUNTEREXAMPLE: ...` or
`NO COUNTEREXAMPLE`. The proof is flagged when the program runs and prints a counterexample. A right proof can only be flagged by a
wrong test, so the false-flag rate on right proofs measures the check's own errors.

Data: the Open Proof Corpus (Dekoninck et al., 2506.21621; INSAIT-Institute/OPC, CC BY-NC-SA 4.0), converted to
$POC_DATA/proof/opc/opc.jsonl (id, problem, solution, label = 1 / 0 when every human judge agrees, None otherwise).
--statement (SIDE-PF dev, 11-04): test a statement alone, before any proof: BrokenMath (Petrov et al., 2510.04721;
INSAIT-Institute/BrokenMath), whose benchmark statements are competition problems perturbed to be false; converted to
$POC_DATA/proof/brokenmath/bm.jsonl (label 0 = false statement, 1 = true: the train split's unperturbed statements and the
benchmark's originals that are themselves statements to prove).
usage (in a lane.sh job; POC_BASE_URL set; $P = the sandbox python):
  $P side/proof_falsify.py <tag> <ids file> [--statement] [--think] [--max_tokens N] [--workers W]
  -> results/proof/pf_<tag>.jsonl, one row per item: id, label, program, out_tokens, finish, run status, last line, flag"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "poc"))
from llm import chat  # noqa: E402
from sandbox import run_python  # noqa: E402

PD = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "proof")
DATA = os.path.join(PD, "opc", "opc.jsonl")
DATA_ST = os.path.join(PD, "brokenmath", "bm.jsonl")

PROMPT = """Below is a competition problem and a proposed solution written by someone else. Do not judge whether the reasoning is \
complete. Your only job is to look for a concrete counterexample by computation.

Write one Python 3 program that tests what the solution states:
1. If the problem asks to find or determine something (all numbers, all functions on a small domain, a maximum, a count), compute \
the true answer for small cases by brute force and compare it with the solution's claimed answer on those cases.
2. For concrete claims the solution makes that can be checked on specific instances (identities, inequalities, divisibility or \
parity claims, claimed values or properties of small cases or of sequences, geometric claims checked in coordinates), test each \
claim on many small or random instances that satisfy exactly the hypotheses the solution states for it.

Rules:
- Test only what the solution actually states, under the hypotheses it states. Do not test claims you made up.
- Use exact arithmetic (integers, fractions.Fraction) where possible; for real-valued claims use random samples and a relative \
tolerance of 1e-9.
- Use only the Python standard library. The program must finish within 10 seconds.
- Print exactly one final line: `COUNTEREXAMPLE: <the claim that fails> | <the instance>` for the first claim that fails, or \
`NO COUNTEREXAMPLE` if every test passes.

Reply with the program in one ```python code block.

Problem:
{problem}

Proposed solution:
{solution}"""


PROMPT_ST = """Below is a competition statement that someone wants proved. It may be false. Do not try to prove it. Your only job \
is to look for a counterexample by computation.

Write one Python 3 program that tests the statement:
- If it makes a claim about specific numbers or objects, compute them directly (by brute force where needed) and check the claim.
- If it claims something for all objects of some kind (all integers, all triangles, all functions with a property), test it on \
many small or random instances that satisfy exactly the statement's hypotheses.

Rules:
- Test the statement exactly as written, under exactly its hypotheses.
- Use exact arithmetic (integers, fractions.Fraction) where possible; for real-valued claims use random samples and a relative \
tolerance of 1e-9.
- Use only the Python standard library. The program must finish within 10 seconds.
- Print exactly one final line: `COUNTEREXAMPLE: <the instance and what fails>` if the statement fails on some instance, or \
`NO COUNTEREXAMPLE` if every test passes.

Reply with the program in one ```python code block.

Statement:
{problem}"""


def code_of(text):
    b = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.S)
    return b[-1] if b else None


def one(x, think, max_tokens, statement=False):
    q = PROMPT_ST.format(problem=x["problem"]) if statement else PROMPT.format(problem=x["problem"], solution=x["solution"])
    r = chat(q, think=think, max_tokens=max_tokens, temperature=0.6 if think else 0.7)
    code = code_of(r["text"])
    run = run_python(code, "", timeout=10) if code else None
    last = (run.stdout.strip().splitlines() or [""])[-1][:500] if run else ""
    flag = bool(run and run.status == "ok" and last.startswith("COUNTEREXAMPLE"))
    return {"id": x["id"], "label": x["label"], "split": x["split"], "model_id": x["model_id"], "program": code,
            "out_tokens": r["out_tokens"], "in_tokens": r["in_tokens"], "finish": r["finish"],
            "status": run.status if run else "no code", "last": last, "stderr": (run.stderr[-300:] if run else ""), "flag": flag}


def main():
    tag, ids_file = sys.argv[1], sys.argv[2]
    think, statement = "--think" in sys.argv, "--statement" in sys.argv
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else (12000 if think else 4096)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 32
    want = set(open(ids_file).read().split())
    X = [x for x in map(json.loads, open(DATA_ST if statement else DATA)) if x["id"] in want]
    os.makedirs(os.path.join(ROOT, "results", "proof"), exist_ok=True)
    out = os.path.join(ROOT, "results", "proof", f"pf_{tag}.jsonl")
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    todo = [x for x in X if x["id"] not in done]
    print(f"SIDE-PF {tag}: {len(todo)} of {len(X)} {'statements' if statement else 'proofs'} to check (think={think}, max_tokens={mt})", flush=True)
    with ThreadPoolExecutor(workers) as ex, open(out, "a") as f:
        fut = [ex.submit(one, x, think, mt, statement) for x in todo]
        for k, fu in enumerate(as_completed(fut)):
            try:
                r = fu.result()
            except Exception as e:   # a request that fails is reported, not retried
                print(f"  failed: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
            f.write(json.dumps(r) + "\n"); f.flush()
            if k % 50 == 0:
                print(f"  {k + 1}/{len(todo)} {r['id']} {r['status']} flag={r['flag']} tok {r['out_tokens']}", flush=True)


if __name__ == "__main__":
    main()
