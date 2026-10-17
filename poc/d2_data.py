"""D2 (results/PREREG_D1.md): S = up to 3 distinct own correct no-think answers per train problem (Qwen3-8B seeds 1-8);
L = the teacher programs of D1 arm A restricted to train problems the student solves in >= 1 of its 8 samples."""
import json
RES = "/NAS/SJ/POSTECH/nlp/results/h2"
S = json.load(open(f"{RES}/d1_split.json")); train = set(S["train"])
P = {p["name"]: p for p in json.load(open(f"{RES}/cc_geometry_full.json"))}
prompt = lambda n: P[n]["description"].strip() + "\n\nWrite a Python 3 program that reads the input from stdin and prints the answer to stdout. Give the program in a single ```python code block."
own = {}
for sd in range(1, 9):
    for r in map(json.loads, open(f"{RES}/cc_full_q8b_plain_s{sd}.jsonl")):
        if r["name"] in train and r["passed_all"] and r["code"] and r["code"] not in own.setdefault(r["name"], []):
            own[r["name"]].append(r["code"])
Sdata = [{"prompt": prompt(n), "code": c, "task": "cc"} for n, cs in own.items() for c in cs[:3]]
learn = {n for n, cs in own.items() if cs}
desc_of = {P[n]["description"].strip(): n for n in train}
A = [json.loads(l) for l in open(f"{RES}/d1_train_A.jsonl")]
L = [r for r in A if desc_of.get(r["prompt"].split("\n\nWrite a Python 3 program that reads the input")[0].strip()) in learn]
for fn, rows in (("d2_S.jsonl", Sdata), ("d2_L.jsonl", L)):
    open(f"{RES}/{fn}", "w").write("".join(json.dumps(x) + "\n" for x in rows))
print("learnable train problems", len(learn), "| S examples", len(Sdata), "| L examples", len(L))
