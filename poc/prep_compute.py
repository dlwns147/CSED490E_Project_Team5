"""Idea 44 (docs/notes/IDEAS_COMPUTATION.md): math computation sets, prepared into $POC_DATA/compute/ (not in the repository).
- euler_dev.json: Project Euler problems from PECC (2404.18766; github.com/hallerpatrick/pecc, problems 1-825 with answers), 120 sampled
  evenly over three difficulty bands (5-25, 30-50, 55-100 %) for the pilot. Old problems: answers are public, so runs need a memorization control.
  The statement text comes from HF alexandonian/project-euler (question_latex, problems 1-928), not from PECC: PECC's text drops the
  markup, so 2^{15} reads "215" and 10^{18} reads "1018" (85 of the 120 sampled statements lose math this way; found 2026-11-12).
- euler_test.json: MathArena's split, problems 943-992 (HF MathArena/project_euler, late 2025), answers from the public list
  github.com/lucky-bai/projecteuler-solutions (Solutions.md). Held for the report; not used in the pilot.
- oeis.json: the integer-sequence tasks of 2411.04372 (github.com/ceodspspectrum/oeis-sequence-benchmark), the "contemporary" half
  (sequences added after July 2024), easy and hard, with their terms and offset.
usage: python poc/prep_compute.py <nlp_data dir>"""
import glob, json, os, random, re, sys

D = sys.argv[1]
out = os.path.join(D, "compute")
os.makedirs(out, exist_ok=True)

E = {}
for f in glob.glob(f"{D}/euler_dl/pecc/dataset/euler/*.json"):
    for x in json.load(open(f)):
        E[x["euler_id"]] = {"id": f"pe{x['euler_id']}", "problem": x["problem"], "answer": str(x["solution"]).strip(), "difficulty": x["difficulty"]}
import pyarrow.parquet as pq
TEX = {str(r["id"]).strip(): r for r in pq.read_table(f"{D}/euler_dl/hf_alex/full.parquet").to_pylist()}
for k, e in E.items():
    t = TEX[str(k)]
    assert str(t["numerical_answer"]).strip() == e["answer"], k
    e["problem"] = t["question_latex"]
rng = random.Random(0)
dev = []
for lo, hi in [(5, 25), (30, 50), (55, 100)]:
    band = sorted((e for e in E.values() if lo <= e["difficulty"] <= hi), key=lambda e: int(e["id"][2:]))
    dev += rng.sample(band, 40)
json.dump(dev, open(f"{out}/euler_dev.json", "w"), indent=0)

ans = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^(\d+)\.\s+(\S+)", open(f"{D}/euler_dl/Solutions.md").read(), re.M)}
test = []
for r in pq.read_table(f"{D}/euler_dl/matharena/data/train-00000-of-00001.parquet").to_pylist():
    k = int(r["source"].replace("euler", ""))
    test.append({"id": f"pe{k}", "problem": r["problem"], "answer": ans.get(k)})
json.dump(test, open(f"{out}/euler_test.json", "w"), indent=0)

O = []
for lvl in ["Easy", "Hard"]:
    for f in sorted(glob.glob(f"{D}/oeis_dl/repo/data/contemporary/Sequence{lvl}Json_files/*.json")):
        x = json.load(open(f))[0]
        O.append({"id": os.path.basename(f)[:-5], "level": lvl.lower(), "name": x["name"], "comments": "\n".join(x.get("comment") or []),
                  "terms": x["data"].split(","), "offset": int(str(x["offset"]).split(",")[0])})
json.dump(O, open(f"{out}/oeis.json", "w"), indent=0)
print(len(dev), "euler dev;", len(test), "euler test,", sum(t["answer"] is not None for t in test), "with answers;", len(O), "oeis")
