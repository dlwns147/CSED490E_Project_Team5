"""STORM-Qwen3-4B (official TIR inference, 3 samples) regraded with our grader (docs/prereg/PREREG_X7.md STORM pre-registration):
the last \\boxed{} of each sample -> run_nlopt.value_of -> run_nlopt.correct (the same tolerance as every other arm); its own math_verify
grade is shown for reference. Tokens: Qwen3 tokenizer over the generated text (tool outputs it inserted are included: small).
usage: /opt/conda/bin/python poc/analyze_storm.py [set]   (set = mamo_full | x3)"""
import json, os, re, sys
from collections import defaultdict



def value_of(s):   # = run_nlopt.value_of / correct (copied: run_nlopt imports OR-Tools, which /opt/conda lacks; this needs its tokenizer)
    s = (s or "").strip()
    if not s:
        return None
    if "no best solution" in s.lower():
        return "NBS"
    m = re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s.replace(",", ""))
    return float(m[-1]) if m else None


def correct(pred, gold):
    if pred is None:
        return False
    if gold.lower().startswith("no best"):
        return pred == "NBS"
    if pred == "NBS":
        return False
    g = float(gold)
    return abs(pred - g) <= max(1e-2, 1e-3 * abs(g))


def boxed(t):
    i = (t or "").rfind("\\boxed{")
    if i < 0:
        return None
    j, d = i + 7, 1
    while j < len(t) and d:
        d += {"{": 1, "}": -1}.get(t[j], 0); j += 1
    return t[i + 7:j - 1]


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "mamo_full"
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("/SSD/huggingface/tangzhy/STORM-Qwen3-4B")
    R = [json.loads(l) for l in open(f"/SSD/lean_postech/storm/out_{st}/data_with_correctness.jsonl")]
    by = defaultdict(lambda: [0, 0, 0, 0]); rows = []
    for r in R:
        for k, g in enumerate(r["gen"]):
            b = boxed(g); pred = value_of(b) if b is not None else None
            ok = correct(pred, str(r["gt_answer"])); n = len(tok(g)["input_ids"])
            x = by[r["data_source"]]; x[0] += ok; x[1] += r["correctness_math_verify"][k]; x[2] += n; x[3] += 1
            rows.append(dict(id=r["id"], src=r["data_source"], sample=k + 1, gold=str(r["gt_answer"]), boxed=b, pred=pred, correct=ok,
                             own=r["correctness_math_verify"][k], out_tokens=n, calls=g.count("```output")))
    tot = [sum(v[i] for v in by.values()) for i in range(4)]
    for s_, v in list(by.items()) + [("all", tot)]:
        print(f"STORM {st} {s_:13s}: our grader {100 * v[0] / v[3]:.1f}% | its own grader {100 * v[1] / v[3]:.1f}% | tokens/sample {v[2] / v[3]:.0f} (n={v[3]})")
    with open(f"results/x3/storm_{st}_regraded.jsonl", "w") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")
