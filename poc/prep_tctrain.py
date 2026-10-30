"""TC-RL (docs/prereg/PREREG_TCRL.md): training items for plain RL on tool calls from ToolACE (Team-ACE/ToolACE, data.json, Apache-2.0;
downloaded to $POC_DATA/toolace/data.json). Kept: single-turn dialogues (user, assistant); function names that are not Python-style (BFCL's
prompt-mode format: ToolACE has many like "Market Trends API") are rewritten, in the docs and in the answer, with "_" for every other
character; kept if the answer either decodes into calls of the listed functions or makes no call; dropped: any item whose
request text equals a BFCL item's. The prompt is BFCL's system prompt (as poc/prep_tc.py's items) with ToolACE's function docs.
Writes $POC_DATA/toolace/tc_train_items.jsonl = {id, system, user, functions, gold: [[name, {arg: value}], ...] or [] (no call)}.
usage: python prep_tctrain.py"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tc_reward import decode  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
MARK = "Here is a list of functions in json format that you can invoke.\n"
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def functions(system):
    i = system.index("[", system.index("Here is a list of functions in JSON format that you can invoke:"))
    return json.JSONDecoder().raw_decode(system[i:])[0]


def main():
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
