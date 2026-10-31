"""MT (docs/prereg/PREREG_MT.md): multi-turn function calling (BFCL v4 multi_turn_base, prompt mode), where the free check is the
environment's own error message at every step. One arm per run (each arm is its own trajectory: a step changes the state the next step
sees). Per item: BFCL's system prompt with the involved classes' function docs, then each turn's user message; within a turn the model
answers, its calls ([func(arg=value), ...], decoded as BFCL's default_decode_execute_prompting) run in BFCL's own environment
classes (multi_turn_utils.execute_multi_turn_func_call), each result goes back as a tool message, until the model answers without a
decodable call (the turn ends) or after 20 steps (BFCL's limit: the item fails). Arms, per step:
  N  non-thinking (2,048-token cap)
  T  thinking (8,192-token cap)
  E  the free check at every step: non-thinking, but thinking for the step after any call of the previous step (same turn) returned
     an error (an "Error during execution" string or a JSON object with an "error" key); the failed calls and errors stay in the context
  F  thinking for the first step of each turn (the new request), then as E
Rows (results/tc/mt_<tag>_<arm>_s<seed>.jsonl): per turn, per step {calls, think, tok, err, end}; the item's output tokens; graded
offline by poc/grade_mt.py (BFCL's multi_turn_checker). Rows resume.
usage: python run_mt.py <tag> <arm N|T|E|F> <seed>     (MT_SUBSET=i/k: items i, i+k, ... only — the smoke; MT_WORKERS, default 8)"""
import ast, copy, json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.dont_write_bytecode = True   # the BFCL package is imported read-only from the grader venv (through $POC_DATA/bfcl/pkg)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_msgs  # noqa: E402
from run_nlopt import _rows  # noqa: E402

PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
sys.path.insert(0, os.path.join(PD, "bfcl", "pkg"))
import bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils as U  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
DATA = os.environ.get("MT_ITEMS") or os.path.join(PD, "bfcl", "mt_items.jsonl")
NMAX, TMAX, STEPS = 2048, 8192, 20


# BFCL's prompt-mode decoder (bfcl_eval.model_handler.utils: default_decode_execute_prompting, ast_parse for Python,
# resolve_ast_call, resolve_ast_by_type, parse_nested_value, decoded_output_to_execution_list), copied because that module imports
# parsers the client venv lacks
def _call(elem):
    parts, f = [], elem.func
    while isinstance(f, ast.Attribute):
        parts.append(f.attr); f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return {".".join(reversed(parts)): {a.arg: _val(a.value) for a in elem.keywords}}


def _val(v):
    if isinstance(v, ast.Constant):
        return "..." if v.value is Ellipsis else v.value
    if isinstance(v, ast.UnaryOp):
        return -v.operand.value
    if isinstance(v, ast.List):
        return [_val(x) for x in v.elts]
    if isinstance(v, ast.Dict):
        return {_val(k): _val(x) for k, x in zip(v.keys, v.values)}
    if isinstance(v, ast.BinOp):
        return eval(ast.unparse(v))
    if isinstance(v, ast.Name):
        return v.id
    if isinstance(v, ast.Call):
        return ast.unparse(v) if not v.keywords else _call(v)
    if isinstance(v, ast.Tuple):
        return tuple(_val(x) for x in v.elts)
    if isinstance(v, ast.Lambda):
        return eval(ast.unparse(v.body[0].value))
    if isinstance(v, ast.Subscript):
        try:
            return ast.unparse(v.body[0].value)
        except Exception:
            return ast.unparse(v.value) + "[" + ast.unparse(v.slice) + "]"
    raise Exception(f"Unsupported AST type: {type(v)}")


def _nested(v):
    if isinstance(v, dict):
        if all(isinstance(x, dict) for x in v.values()):
            f = list(v)[0]
            return f"{f}({', '.join(f'{k}={_nested(x)}' for k, x in v[f].items())})"
        return "{" + ", ".join(f"'{k}': {_nested(x)}" for k, x in v.items()) + "}"
    return repr(v)


def decode(text):
    s = text.strip("`\n ")
    if not s.startswith("["):
        s = "[" + s
    if not s.endswith("]"):
        s = s + "]"
    p = ast.parse(s.strip().strip("'"), mode="eval")
    calls = [_call(p.body)] if isinstance(p.body, ast.Call) else []
    if not calls:
        for e in p.body.elts:
            assert isinstance(e, ast.Call)
            calls.append(_call(e))
    return [f"{k}({', '.join(f'{a}={_nested(x)}' for a, x in v.items())})" for c in calls for k, v in c.items()]


def is_err(res):
    if res.startswith("Error during execution"):
        return True
    try:
        d = json.loads(res)
    except Exception:
        return False
    return isinstance(d, dict) and "error" in d


def answer(msgs, think, seed):
    o = chat_msgs(msgs, think=think, max_tokens=TMAX if think else NMAX, temperature=0.7, seed=seed)
    t = o["text"]
    if "</think>" in t:
        t = t.split("</think>")[-1]
    if "<think>" in t:   # the think never closed (cap reached): no answer
        t = ""
    return t.strip(), o["out_tokens"], o["finish"]


def run_item(p, tag, arm, seed):
    name = f"{tag}_{arm}_s{seed}"
    cfg, cls, lc = p["initial_config"], p["involved_classes"], "long_context" in p["cat"]
    U.execute_multi_turn_func_call([], cfg, cls, name, p["id"], long_context=lc)   # fresh instances for this trajectory
    msgs = [{"role": "system", "content": p["system"]}]
    turns, tok, quit_ = [], 0, False
    for ti, um in enumerate(p["turns"]):
        msgs += um
        steps, prev_err = [], False   # an error flags the next step of the same request only
        for k in range(STEPS + 1):
            think = arm == "T" or (arm in ("E", "F") and prev_err) or (arm == "F" and k == 0)
            sd = seed * 100003 + zlib.crc32(f"{p['id']}/{ti}/{k}".encode()) % 99991
            text, n, fin = answer(msgs, think, sd)
            tok += n
            msgs.append({"role": "assistant", "content": text})
            try:
                calls = decode(text)
            except Exception:
                calls = []
            if not calls:
                steps.append({"calls": [], "think": think, "tok": n, "fin": fin, "text": text[:300]})
                break
            res, _ = U.execute_multi_turn_func_call(calls, cfg, cls, name, p["id"], long_context=lc)
            errs = [is_err(r) for r in res]
            for c, r in zip(calls, res):
                msgs.append({"role": "tool", "name": c, "content": r})
            steps.append({"calls": calls, "think": think, "tok": n, "fin": fin, "err": errs, "res": [r[:200] for r in res]})
            prev_err = any(errs)
            if k == STEPS:
                quit_ = True
        turns.append(steps)
        if quit_:
            break
    for c in cls:   # free the trajectory's instances
        U.__dict__.pop(re.sub(r"[-./:]", "_", f"{name}_{p['id']}_{c}_instance"), None)
    return {"id": p["id"], "cat": p["cat"], "arm": arm, "seed": seed, "turns": turns, "tok": tok, "force_quit": quit_,
            "n_think": sum(s["think"] for t in turns for s in t), "n_steps": sum(len(t) for t in turns)}


def main():
    tag, arm, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    assert arm in ("N", "T", "E", "F")
    P = [json.loads(l) for l in open(DATA)]
    if os.environ.get("MT_SUBSET"):
        i, k = map(int, os.environ["MT_SUBSET"].split("/")); P = P[i::k]
    os.makedirs(RES, exist_ok=True)
    path = f"{RES}/mt_{tag}_{arm}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    todo = [p for p in P if p["id"] not in done]
    print(f"MT {tag} {arm} s{seed}: {len(todo)} of {len(P)} items to run", flush=True)
    with ThreadPoolExecutor(int(os.environ.get("MT_WORKERS", 8))) as ex, open(path, "a") as f:
        fs = {ex.submit(run_item, p, tag, arm, seed): p["id"] for p in todo}
        for j, fu in enumerate(as_completed(fs)):
            try:
                r = fu.result()
            except Exception as e:
                print(f"  {fs[fu]}: {type(e).__name__}: {e}", flush=True)
                continue
            f.write(json.dumps(r) + "\n"); f.flush()
            if j % 20 == 0:
                print(f"  {j + 1}/{len(todo)} {r['id']} steps {r['n_steps']} think {r['n_think']} tok {r['tok']}", flush=True)


if __name__ == "__main__":
    main()
