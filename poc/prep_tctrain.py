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


def main():
    if "--ace" in sys.argv:
        return main_ace()
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
