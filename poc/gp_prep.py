"""GridPuzzle (Tyagi et al. 2024, github.com/Mihir3009/GridPuzzle, MIT): 274 Puzzle Baron logic grid puzzles written by people.

Usage: python3 -I poc/gp_prep.py <GridPuzzle.csv> <out grid.jsonl>
Each row: id, size (categories x items), puzzle text, cats [[name, values]] (the first category is the ordered one),
gold {category: [values in the order of the first category's values]} for the other categories, split (dev: the first 8 of each size by id).
Rows whose answer does not parse into the listed values are dropped and counted.
"""
import csv
import json
import re
import sys


def main():
    csv.field_size_limit(10 ** 8)
    R = list(csv.DictReader(open(sys.argv[1], encoding="utf-8", errors="replace")))
    out, bad = [], 0
    for r in R:
        head = r["question"].split("Clues:")[0]
        cats = [[l.split(" : ", 1)[0].strip(), [v.strip() for v in l.split(" : ", 1)[1].strip().rstrip(".").split(",")]]
                for l in head.split("\n") if re.match(r"^[^:]{1,40} : ", l)]
        rows = [[x.strip() for x in l.split("|")] for l in r["answer"].strip().split("\n") if l.strip()]
        n = len(cats[0][1]) if cats else 0
        ok = cats and all(len(v) == n for _, v in cats) and len(rows) == n and all(len(x) == len(cats) for x in rows)
        if ok:
            order = {x[0].lower(): x for x in rows}
            ok = all(v.lower() in order for v in cats[0][1]) and all(
                sorted(x[k].lower() for x in rows) == sorted(v.lower() for v in cats[k][1]) for k in range(1, len(cats)))
        if not ok:
            bad += 1
            continue
        gold = {cats[k][0]: [order[v.lower()][k] for v in cats[0][1]] for k in range(1, len(cats))}
        out.append({"id": f"gp-{int(r['id']):04d}", "size": f"{len(cats)}*{n}", "puzzle": r["question"].strip(), "cats": cats, "gold": gold})
    out.sort(key=lambda x: x["id"])
    seen = {}
    for x in out:   # dev: the first 8 puzzles of each size by id, read while writing prompts; the rest is test
        seen[x["size"]] = seen.get(x["size"], 0) + 1
        x["split"] = "dev" if seen[x["size"]] <= 8 else "test"
    with open(sys.argv[2], "w") as f:
        for x in out:
            f.write(json.dumps(x) + "\n")
    print(f"kept {len(out)}, dropped {bad}")


if __name__ == "__main__":
    main()
