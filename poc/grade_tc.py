"""TC-1 (docs/prereg/PREREG_TC.md): grade every response of run_tc.py with BFCL's own decoder and AST checker (prompt mode, Python;
irrelevance = no call, relevance = some call, as its eval_runner), and run the free check: schema validation of the decoded calls
against the function docs, no gold — fail = a malformed call (the text names a provided function with "(" but does not decode into
calls), an unknown function, a missing required or an unknown parameter, a value of the wrong type, or a value outside its enum;
no call at all passes (None for an optional parameter = unset). Writes results/tc/grades_<tag>_s<seed>.json = {id: {arm: {"ok", "err", "chk", "why", "calls"}}} for the arms
N, T, SB ("calls" = the decoded calls in a canonical form, for agreement; "none" for no call). Runs on the login node:
  /home1/leesangjun/venvs/bfcl/bin/python poc/grade_tc.py <tag> [seed ...]   (default seeds 1 2 3)"""
import copy, json, os, sys

from bfcl_eval.constants.enums import Language, ReturnFormat
from bfcl_eval.eval_checker.ast_eval.ast_checker import ast_checker
from bfcl_eval.model_handler.utils import default_decode_ast_prompting
from bfcl_eval.utils import is_empty_output, is_function_calling_format_output

DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bfcl")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
MODEL = "Qwen/Qwen3-8B"   # BFCL's prompt-mode Qwen3 entry: only its underscore_to_dot (False) is read by the checker
TYPES = {"string": (str,), "integer": (int,), "float": (int, float), "boolean": (bool,), "array": (list, tuple), "tuple": (list, tuple),
         "dict": (dict,)}


def rows(path):
    return {r["id"]: r for r in (json.loads(l) for l in open(path))} if os.path.exists(path) else {}


def decode(text):
    try:
        d = default_decode_ast_prompting(text or "", ReturnFormat.PYTHON, False)
    except Exception:
        return None
    return d


def schema_check(text, d, functions):
    """('pass' | 'fail', reason): the free check, from the response and the function docs only"""
    doc = {f["name"]: f for f in functions}
    if d is None or not is_function_calling_format_output(d) or is_empty_output(d):
        named = [n for n in doc if n + "(" in (text or "")]
        return ("fail", f"malformed call to {named[0]}") if named else ("pass", "no call")
    for c in d:
        (name, args), = c.items()
        if name not in doc:
            return "fail", f"unknown function {name}"
        par = doc[name].get("parameters", {})
        props, req = par.get("properties", {}), par.get("required", [])
        for k in req:
            if k not in args:
                return "fail", f"{name}: missing {k}"
        for k, v in args.items():
            if k not in props:
                return "fail", f"{name}: unknown parameter {k}"
            if v is None and k not in req:   # None for an optional parameter = left unset
                continue
            t = props[k].get("type")
            if t in TYPES and (not isinstance(v, TYPES[t]) or (t in ("integer", "float") and isinstance(v, bool))):
                return "fail", f"{name}: {k} is {type(v).__name__}, not {t}"
            if "enum" in props[k] and not isinstance(v, (list, dict)) and v not in props[k]["enum"]:
                return "fail", f"{name}: {k}={v!r} not in its enum"
    return "pass", "ok"


def grade(cat, functions, gt, text, d):
    """BFCL's verdict (eval_runner: _evaluate_single_relevance_entry / _evaluate_single_ast_entry) and its error type"""
    if "irrelevance" in cat or cat == "live_relevance":
        call = d is not None and not is_empty_output(d)
        ok = (not call) if "irrelevance" in cat else call
        return ok, ("" if ok else ("irrelevance:called" if "irrelevance" in cat else "relevance:no_call"))
    if d is None:
        return False, "ast_decoder:decoder_failed"
    if not is_function_calling_format_output(d):
        return False, "ast_decoder:decoder_wrong_output_format"
    r = ast_checker(copy.deepcopy(functions), copy.deepcopy(d), copy.deepcopy(gt), Language.PYTHON, cat, MODEL)
    return bool(r["valid"]), ("" if r["valid"] else r.get("error_type", "?"))


def canon(d):
    if d is None or not is_function_calling_format_output(d) or is_empty_output(d):
        return "none"
    return json.dumps(sorted(json.dumps(c, sort_keys=True, default=str) for c in d))


def main():
    tag = sys.argv[1]
    seeds = [int(s) for s in sys.argv[2:]] or [1, 2, 3]
    items = {x["id"]: x for x in (json.loads(l) for l in open(f"{DATA}/tc_items.jsonl"))}
    gts = {x["id"]: x["ground_truth"] for x in (json.loads(l) for l in open(f"{DATA}/tc_answers.jsonl"))}
    for s in seeds:
        C, T, SB = (rows(f"{RES}/{tag}_{a}_s{s}.jsonl") for a in ("cheap", "think", "sb"))
        out = {}
        for i, x in items.items():
            g = {}
            for arm, text in (("N", C.get(i, {}).get("n_text")), ("T", T.get(i, {}).get("text")), ("SB", SB.get(i, {}).get("text"))):
                if text is None:
                    continue
                d = decode(text)
                ok, err = grade(x["cat"], x["functions"], gts[i], text, d)
                chk, why = schema_check(text, d, x["functions"])
                g[arm] = {"ok": ok, "err": err, "chk": chk, "why": why, "calls": canon(d)}
            if g:
                out[i] = g
        json.dump(out, open(f"{RES}/grades_{tag}_s{s}.json", "w"))
        acc = {a: [v[a]["ok"] for v in out.values() if a in v] for a in ("N", "T", "SB")}
        print(tag, s, {a: f"{100 * sum(v) / max(1, len(v)):.1f}% of {len(v)}" for a, v in acc.items()},
              "check fails on N:", sum(v["N"]["chk"] == "fail" for v in out.values() if "N" in v), flush=True)


if __name__ == "__main__":
    main()
