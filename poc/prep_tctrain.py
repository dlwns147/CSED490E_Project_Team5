"""TC-RL (docs/prereg/PREREG_TCRL.md): training items for plain RL on tool calls from ToolACE (Team-ACE/ToolACE, data.json, Apache-2.0;
downloaded to $POC_DATA/toolace/data.json). Kept: single-turn dialogues (user, assistant); function names that are not Python-style (BFCL's
prompt-mode format: ToolACE has many like "Market Trends API") are rewritten, in the docs and in the answer, with "_" for every other
character; kept if the answer either decodes into calls of the listed functions or makes no call; dropped: any item whose
request text equals a BFCL item's. The prompt is BFCL's system prompt (as poc/prep_tc.py's items) with ToolACE's function docs.
Writes $POC_DATA/toolace/tc_train_items.jsonl = {id, system, user, functions, gold: [[name, {arg: value}], ...] or [] (no call)}.
usage: python prep_tctrain.py
--ace (PREREG_LCM addendum ACE): ACEBench's English single-call data (github ACEBench/ACEBench, MIT; cloned to
$POC_DATA/ext/acebench_src, data_all/data_en: normal atom / single / parallel / similar-API / preference / multi-turn, special
incomplete / error-param / irrelevant; agent left out: it needs ACEBench's environment) as items of the same form ->
$POC_DATA/acebench/tc_items.jsonl, with cat. The prompt is the same BFCL system prompt with ACEBench's function docs ("arguments" read
as "parameters"; "object" / "number" written as BFCL's "dict" / "float"), then ACEBench's current time and, for preference items, the
user's profile; the user turn is ACEBench's conversation text. gold: the calls (repeated functions' "_<n>" suffixes removed, as
ACEBench's checker does); special items have gold [] (no call is right — BFCL's irrelevance convention; ACEBench's own check that
the reply names the problem is not applied); gold_alt: further accepted call lists where ACEBench lists alternatives."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tc_reward import decode  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
MARK = "Here is a list of functions in json format that you can invoke.\n"
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def functions(system):
    i = system.index("[", system.index("Here is a list of functions in JSON format that you can invoke:"))
    return json.JSONDecoder().raw_decode(system[i:])[0]


ACE_CATS = ("normal_atom_bool", "normal_atom_enum", "normal_atom_list", "normal_atom_number", "normal_atom_object_deep",
            "normal_atom_object_short", "normal_single_turn_single_function", "normal_single_turn_parallel_function", "normal_similar_api",
            "normal_preference", "normal_multi_turn_user_adjust", "normal_multi_turn_user_switch", "special_incomplete",
            "special_error_param", "special_irrelevant")


def ace_doc(x):
    """ACEBench's schema in BFCL's words: "object" -> "dict", "number" -> "float" (recursively)"""
    if isinstance(x, dict):
        return {k: ({"object": "dict", "number": "float"}.get(v, v) if k == "type" and isinstance(v, str) else ace_doc(v)) for k, v in x.items()}
    if isinstance(x, list):
        return [ace_doc(v) for v in x]
    return x


def main_ace():
    bfcl = [json.loads(l) for l in open(f"{DATA}/bfcl/tc_items.jsonl")]
    head = bfcl[0]["system"][:bfcl[0]["system"].index(MARK) + len(MARK)]
    src = f"{DATA}/ext/acebench_src/data_all/data_en"
    out, why = [], {}
    for c in ACE_CATS:
        A = {a["id"]: a["ground_truth"] for a in map(json.loads, open(f"{src}/possible_answer/data_{c}.json"))}
        for r in map(json.loads, open(f"{src}/data_{c}.json")):
            fs = []
            for f in r["function"]:
                f = dict(f)
                if "parameters" not in f and "arguments" in f:
                    f["parameters"] = f.pop("arguments")
                f.pop("results", None); f.pop("tags", None)
                if not NAME.match(f["name"]):   # as ToolACE's (two special items' functions start with a digit; no gold call)
                    new = re.sub(r"[^A-Za-z0-9_.]", "_", f["name"])
                    f["name"] = "_" + new if new[0].isdigit() else new
                    why["renamed"] = why.get("renamed", 0) + 1
                fs.append(ace_doc(f))
            gt = A[r["id"]]
            if c.startswith("special"):
                gold, alt = [], []
            else:
                alts = [[[re.sub(r"_\d+$", "", n), a] for n, a in g.items()] for g in (gt if isinstance(gt, list) else [gt])]
                gold, alt = alts[0], alts[1:]
            names = {f["name"] for f in fs}
            if any(n not in names for g in [gold] + alt for n, _ in g):
                why["answer"] = why.get("answer", 0) + 1; continue
            sysm = head + json.dumps(fs, indent=4) + "\n"
            if r.get("time"):
                sysm += "\n" + r["time"].strip() + "\n"
            if r.get("profile"):
                sysm += "\nThe user's profile:\n" + json.dumps(r["profile"], indent=4) + "\n"
            out.append({"id": f"ace_{r['id']}", "cat": c, "system": sysm, "user": r["question"].strip(), "functions": fs, "gold": gold,
                        "gold_alt": alt})
    os.makedirs(f"{DATA}/acebench", exist_ok=True)
    with open(f"{DATA}/acebench/tc_items.jsonl", "w") as f:
        for p in out:
            f.write(json.dumps(p) + "\n")
    print(len(out), "kept;", sum(not p["gold"] for p in out), "with no call;", sum(bool(p["gold_alt"]) for p in out), "with alternatives;",
          "dropped / flagged", why)


PREF_TYPES = {"object": "dict", "number": "float", "str": "string", "int": "integer", "bool": "boolean", "list": "array", "dict": "dict",
              "float": "float", "tuple": "tuple", "string": "string", "integer": "integer", "boolean": "boolean", "array": "array"}


def pref_type(t):
    """a JSON-schema or xLAM type ("List[int], optional", "str") in BFCL's words; None where unknown (left unchecked)"""
    t = re.sub(r",\s*optional\s*$", "", str(t).strip(), flags=re.I)
    t = re.sub(r"\[.*$", "", t).strip().lower()
    return PREF_TYPES.get(t)


def pref_fun(f):
    """a function doc in BFCL's form: types renamed, an xLAM parameter dict ({name: {description, type, default}}) as properties with
    required = the parameters not marked optional and without a default; None where no usable name"""
    f = json.loads(f) if isinstance(f, str) else f
    f = dict(f.get("function", f))
    par = f.get("parameters") or {}
    if "required" in f:   # When2Call writes the required list beside the parameters
        par = dict(par, required=sorted(set(par.get("required", []) or []) | set(f.pop("required") or [])))
    if "properties" not in par:
        req = [k for k, v in par.items() if isinstance(v, dict) and "optional" not in str(v.get("type", "")).lower() and "default" not in v]
        par = {"type": "dict", "properties": par, "required": req}
    props = {}
    for k, v in (par.get("properties") or {}).items():
        v = dict(v) if isinstance(v, dict) else {}
        t = pref_type(v.get("type", ""))
        if t:
            v["type"] = t
        else:
            v.pop("type", None)
        props[k] = v
    f["parameters"] = {"type": "dict", "properties": props, "required": [k for k in par.get("required", []) or [] if k in props]}
    return f if f.get("name") else None


def pyval(v):
    if isinstance(v, bool) or v is None:
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(pyval(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{json.dumps(str(k))}: {pyval(x)}" for k, x in v.items()) + "}"
    return repr(v)


def pycalls(calls, ren):
    """[{name, arguments}] -> BFCL's prompt-mode answer "[f(a=1), g(b="x")]"; None if malformed"""
    out = []
    for c in calls:
        if not isinstance(c, dict) or not isinstance(c.get("arguments", {}), dict) or not c.get("name"):
            return None
        a = c.get("arguments") or {}
        if not all(isinstance(k, str) and k.isidentifier() for k in a):
            return None
        out.append(f"{ren.get(c['name'], c['name'])}(" + ", ".join(f"{k}={pyval(v)}" for k, v in a.items()) + ")")
    return "[" + ", ".join(out) + "]"


def main_pref():
    """--pref (PREREG_LCM addendum SEL-DATA): public preference pairs as verifier training pairs in our prompt format ->
    $POC_DATA/toolace/tc_pref_pairs.jsonl {id, src, kind, system, user, functions, right, wrong}. Sources (single-turn only):
    ToolPref-Pairwise-30K's discriminative split (RioLee/ToolPref-Pairwise-30K toolrm_train_disc, CC-BY-NC-SA-4.0; ToolRM 2510.26167):
    pairs of two calls with the chosen one right by its rule (score 1.0) and the rejected one not; its call / no-call pairs are left out
    (every chosen answer there makes a call: no request in it has no call right); When2Call (nvidia/When2Call train_pref, CC-BY-4.0;
    2504.18851): pairs of a call and a no-call answer (a question back, or a statement that it cannot be done; both are "[]", as our
    no-call answer). Kept if both answers pass our free check (tc_reward.check: the verifier only sees passing answers), the rejected
    one is wrong by our grading with the chosen one as gold (tc_reward.right) and the request text is none of BFCL's, ACEBench's or the
    ToolACE items'"""
    from tc_reward import check, canon as tcanon, right
    seen = set()
    for f in ("bfcl/tc_items.jsonl", "acebench/tc_items.jsonl", "toolace/tc_train_items.jsonl"):
        seen |= {p["user"].strip() for p in map(json.loads, open(f"{DATA}/{f}")) if isinstance(p["user"], str)}
    bfcl = [json.loads(l) for l in open(f"{DATA}/bfcl/tc_items.jsonl")]
    head = bfcl[0]["system"][:bfcl[0]["system"].index(MARK) + len(MARK)]
    out, why = [], {}

    def add(src, k, fs, user, right_calls, wrong_calls):
        if user.strip() in seen:
            why[src + " in eval sets"] = why.get(src + " in eval sets", 0) + 1; return
        ren = {}
        for f in fs:
            if not NAME.match(f["name"]):
                new = re.sub(r"[^A-Za-z0-9_.]", "_", f["name"])
                ren[f["name"]] = f["name"] = "_" + new if new[0].isdigit() else new
        txt = [("[]" if c == [] else pycalls(c, ren)) for c in (right_calls, wrong_calls)]
        if None in txt or not all(check(t, fs) for t in txt) or tcanon(txt[0]) == tcanon(txt[1]):
            why[src + " check"] = why.get(src + " check", 0) + 1; return
        if right(txt[1], decode(txt[0]), fs):   # the rejected answer is right by our grading (e.g. a default written out)
            why[src + " same by our grading"] = why.get(src + " same by our grading", 0) + 1; return
        kind = "cc" if right_calls and wrong_calls else ("nr" if not right_calls else "cr")
        out.append({"id": f"{src}_{k}", "src": src, "kind": kind, "system": head + json.dumps(fs, indent=4) + "\n", "user": user,
                    "functions": fs, "right": txt[0], "wrong": txt[1]})

    def tool_calls(t):
        return [json.loads(x) for x in re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", t, re.S)]
    import pyarrow.parquet as pq
    for k, r in enumerate(pq.read_table(f"{DATA}/ext/toolrm/toolrm_train_disc.parquet").to_pylist()):
        ch, rj = r["chosen"], r["rejected"]
        if [m["role"] for m in ch] != ["system", "user", "assistant"] or [m["role"] for m in rj] != ["system", "user", "assistant"]:
            why["toolpref multi-turn"] = why.get("toolpref multi-turn", 0) + 1; continue
        if not (r["chosen_score"] == 1.0 and r["rejected_score"] < 1.0):
            why["toolpref chosen not right"] = why.get("toolpref chosen not right", 0) + 1; continue
        try:
            a, b = tool_calls(ch[2]["content"]), tool_calls(rj[2]["content"])
            tl = re.findall(r"<tools>\s*(.*?)\s*</tools>", ch[0]["content"], re.S)[-1]   # the first is the instruction's "<tools></tools>"
            fs = [pref_fun(x) for x in tl.splitlines() if x.strip()]
        except (ValueError, AttributeError):
            why["toolpref parse"] = why.get("toolpref parse", 0) + 1; continue
        if not a or not b or None in fs:
            why["toolpref call / no call"] = why.get("toolpref call / no call", 0) + 1; continue
        add("toolpref", k, fs, ch[1]["content"], a, b)
    for k, r in enumerate(map(json.loads, open(f"{DATA}/ext/when2call/when2call_train_pref.jsonl"))):
        try:
            fs = [pref_fun(x) for x in r["tools"]]
            cs = []
            for m in (r["chosen_response"], r["rejected_response"]):
                t = m["content"]
                x = re.search(r"<TOOLCALL>\s*(.*?)\s*</TOOLCALL>", t, re.S)
                cs.append(json.loads(x.group(1)) if x else [])
        except (ValueError, AttributeError):
            why["when2call parse"] = why.get("when2call parse", 0) + 1; continue
        if None in fs or bool(cs[0]) == bool(cs[1]) or len(r["messages"]) != 1:
            why["when2call same kind"] = why.get("when2call same kind", 0) + 1; continue
        add("when2call", k, fs, r["messages"][0]["content"], cs[0], cs[1])
    with open(f"{DATA}/toolace/tc_pref_pairs.jsonl", "w") as f:
        for p in out:
            f.write(json.dumps(p) + "\n")
    from collections import Counter
    print(len(out), "pairs;", dict(Counter((p["src"], p["kind"]) for p in out)), "dropped", why)


def main():
    if "--ace" in sys.argv:
        return main_ace()
    if "--pref" in sys.argv:
        return main_pref()
    bfcl = [json.loads(l) for l in open(f"{DATA}/bfcl/tc_items.jsonl")]
    head = bfcl[0]["system"][:bfcl[0]["system"].index(MARK) + len(MARK)]
    seen = {p["user"].strip() for p in bfcl}
    out, why = [], {}
    for k, e in enumerate(json.load(open(f"{DATA}/toolace/data.json"))):
        c = e["conversations"]
        if len(c) != 2 or c[0]["from"] != "user" or c[1]["from"] != "assistant":
            why["multi-turn"] = why.get("multi-turn", 0) + 1; continue
        try:
            fs = functions(e["system"])
        except (ValueError, KeyError):
            why["docs"] = why.get("docs", 0) + 1; continue
        if not fs or not all(isinstance(f, dict) and f.get("name") for f in fs):
            why["names"] = why.get("names", 0) + 1; continue
        ans = c[1]["value"].strip()
        for f in sorted(fs, key=lambda f: -len(f["name"])):
            if not NAME.match(f["name"]):
                new = re.sub(r"[^A-Za-z0-9_.]", "_", f["name"])
                new = "_" + new if new[0].isdigit() else new
                ans = ans.replace(f["name"] + "(", new + "(")
                f["name"] = new
        if c[0]["value"].strip() in seen:
            why["in BFCL"] = why.get("in BFCL", 0) + 1; continue
        calls = decode(ans) if ans.startswith("[") else []
        if calls is None or any(n not in {f["name"] for f in fs} for n, _ in calls):
            why["answer"] = why.get("answer", 0) + 1; continue
        out.append({"id": f"toolace_{k}", "system": head + json.dumps(fs, indent=4) + "\n", "user": c[0]["value"], "functions": fs,
                    "gold": calls})
    with open(f"{DATA}/toolace/tc_train_items.jsonl", "w") as f:
        for p in out:
            f.write(json.dumps(p) + "\n")
    print(len(out), "kept;", sum(not p["gold"] for p in out), "with no call; dropped", why)


if __name__ == "__main__":
    main()
