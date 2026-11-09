"""GridPuzzle (Tyagi et al. 2024, github.com/Mihir3009/GridPuzzle, MIT): 274 Puzzle Baron logic grid puzzles written by people.

Usage: python3 -I poc/gp_prep.py <GridPuzzle.csv> <out grid.jsonl>
Each row: id, size (categories x items), puzzle text, cats [[name, values]] (the first category is the ordered one),
gold {category: [values in the order of the first category's values]} for the other categories, split (dev: the first 8 of each size by id).
Rows whose answer does not parse into the listed values are dropped and counted.

Second source: python3 -I poc/gp_prep.py --lgp <LogicGridPuzzleData dir> <out grid.jsonl>
Mitra and Baral (EMNLP 2015) as released by Ishay et al. (KR 2023, github.com/azreasoners/gpt-asp-rules, MIT): 150 Puzzle Baron puzzles, the same row format.
Train_50 is dev; Test_50 and Test_2_50_HA are test (Ishay et al.: GPT-4 writing ASP solves 92 of these 100). The first category is the one whose values
are all numbers or months (the ordered one, as in GridPuzzle), else the first listed. Ishay et al.'s three corrections of the story text are applied.
"""
import csv
import json
import os
import re
import sys

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def ordered(vals):
    return all(re.search(r"\d", v) for v in vals) or all(v.lower() in MONTHS for v in vals)


def key(v, vals):   # values of a category whose every value has a number compare by that number, others by their letters and digits
    return re.search(r"\d[\d:.]*", v.replace(",", "")).group() if all(re.search(r"\d", x) for x in vals) and re.search(r"\d", v) else re.sub(r"[^a-z0-9]", "", v.lower())


def ci(path):   # two solution files are spelled Sol_ instead of sol_
    d, b = os.path.split(path)
    return os.path.join(d, next((x for x in os.listdir(d) if x.lower() == b.lower()), b))


def lgp_main(root, dst):
    hint = "Remember, as with all grid-based logic puzzles, no option in any category will ever be used more than once."
    fix = {("test", 12): ["budget, "], ("test", 20): [", or featured people who played the same position", ", and determine the player's position"], ("test", 49): ["budget, "]}
    out, bad = [], 0
    for part, split, base, data, sol in [("train", "dev", 1000, "Train_50/annoated/annotated_Train_{}.txt", "Train_50/Solution/sol_Train_{}.txt"),
                                         ("test", "test", 2000, "Test_50/annotated/annotated_Test_{}.txt", "Test_50/Solution/sol_Test_{}.txt"),
                                         ("test_HA", "test", 3000, "Test_2_50_HA/HA_{}.txt", "Test_2_50_HA/sol_HA_{}.txt")]:
        for i in range(1, 51):
            t = open(os.path.join(root, data.format(i)), encoding="utf-8", errors="replace").read().split("###")[0].replace("\t", "").replace("\n1. ", "\n::1. ")
            parts = t.split("\n::")
            story, clues = parts[0].strip(), parts[-1].strip()
            for x in fix.get((part, i), []):
                story = story.replace(x, "")
            cats = [[q.strip().split("\n")[0].strip(), [v.strip() for v in q.strip().split("\n")[1:] if v.strip()]] for q in parts[1:-1]]
            lines = [re.split(r"\t|,", l.strip()) for l in open(ci(os.path.join(root, sol.format(i))), encoding="utf-8", errors="replace").read().strip().split("\n") if l.strip()]
            n = len(cats[0][1]) if cats else 0
            k0 = next((k for k, (_, v) in enumerate(cats) if ordered(v)), 0)
            cats = [cats[k0]] + cats[:k0] + cats[k0 + 1:]
            col = {}   # solution column of each category, by its set of values ("190 degree" in the list is "190" in some solutions; some have no header line)
            rows = lines[1:] if len(lines) == n + 1 else lines
            for k, (_, vals) in enumerate(cats):
                c = [j for j in range(len(rows[0])) if sorted(key(x[j], vals) for x in rows) == sorted(key(v, vals) for v in vals)] if rows and len(set(map(len, rows))) == 1 else []
                if len(c) == 1:
                    col[k] = c[0]
            if not (n and all(len(v) == n for _, v in cats) and len(rows) == n and len(col) == len(cats)):
                bad += 1
                continue
            order = {key(x[col[0]], cats[0][1]): x for x in rows}
            gold = {cats[k][0]: [next(y for y in cats[k][1] if key(y, cats[k][1]) == key(order[key(v, cats[0][1])][col[k]], cats[k][1])) for v in cats[0][1]] for k in range(1, len(cats))}
            head = "\n".join(f"{a} : {', '.join(v)}." for a, v in cats)
            out.append({"id": f"lgp-{base + i}", "size": f"{len(cats)}*{n}", "puzzle": f"{story} {hint}\n\n{head}\n\nClues:\n{clues}", "cats": cats, "gold": gold, "split": split, "part": part})
    with open(dst, "w") as f:
        for x in out:
            f.write(json.dumps(x) + "\n")
    print(f"kept {len(out)}, dropped {bad}")


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
    lgp_main(*sys.argv[2:4]) if sys.argv[1] == "--lgp" else main()
