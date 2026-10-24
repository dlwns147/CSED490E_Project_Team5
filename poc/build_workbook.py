"""DT-P (docs/prereg/PREREG_DT.md): 2,000 random Lean Workbook statements as unlabeled proof problems (their stored proofs dropped),
in the miniF2F format (the shared header, the statement ending in ':= by'), minus any sharing >= 30% of its 8-gram set with a miniF2F
test statement (informal or formal). usage: python build_workbook.py  -> $POC_DATA/sft/workbook_2k.json"""
import json, os, random, re, sys

DATA = os.environ.get("POC_DATA", "/NAS/SJ/POSTECH/nlp_data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def grams(t, n=8):
    w = re.findall(r"[A-Za-z0-9]+", t.lower())
    return {" ".join(w[k:k + n]) for k in range(max(0, len(w) - n + 1))}


def main():
    M = json.load(open(f"{RES}/x3/minif2f.json"))
    header = M[0]["header"]
    held = [g for m in M if m["split"] == "test" for g in (grams(m["formal_statement"]), grams(m.get("informal_prefix") or "")) if g]
    D = json.load(open(f"{DATA}/stage/unlabeled/lean_workbook.json"))
    rng = random.Random(0); out, dropped = [], 0
    for d in rng.sample(D, 4000):
        st = re.sub(r":=\s*by\s+sorry\s*$", ":= by\n", d["formal_statement"].strip())
        if not st.endswith(":= by\n") or not st.lstrip().startswith("theorem"):
            continue
        g = grams(st) | grams(d.get("natural_language_statement") or "")
        if any(len(g & h) >= 0.3 * min(len(g), len(h)) for h in held):
            dropped += 1; continue
        name = re.match(r"\s*theorem\s+(\S+)", st).group(1)
        out.append({"name": name, "split": "workbook", "header": header, "formal_statement": st,
                    "informal_prefix": d.get("natural_language_statement") or "", "goal": ""})
        if len(out) == 2000:
            break
    json.dump(out, open(f"{DATA}/sft/workbook_2k.json", "w"))
    print(f"wrote {len(out)} statements; dropped {dropped} for overlap with miniF2F test")


if __name__ == "__main__":
    main()
