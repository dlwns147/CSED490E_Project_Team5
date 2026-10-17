"""VIEWS-P5 (results/PREREG_VIEWS.md): factual QA (PopQA) — are knowledge errors shared across a model's views?
1,500 questions stratified by subject popularity (5 bins x 300, seed 0). Views: direct (short answer), recall (write 2-3 facts about
the subject first, then answer), think (thinking on). Correct = any accepted answer string occurs in the answer (the standard PopQA
match). usage: POC_BASE_URL=... python run_popqa.py <tag> <direct|recall|think> <seed>  -> results/x5/qa_<tag>_<view>_s<seed>.jsonl"""
import json, os, random, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x5")


def questions():
    path = f"{RES}/popqa_sample.json"
    if os.path.exists(path):
        return json.load(open(path))
    import datasets
    ds = datasets.load_dataset("akariasai/PopQA", cache_dir="/SSD/huggingface/datasets")["test"]
    rows = [dict(r) for r in ds]
    rows.sort(key=lambda r: int(r["s_pop"]))
    bins = [rows[i * len(rows) // 5:(i + 1) * len(rows) // 5] for i in range(5)]
    rng = random.Random(0)
    out = [{"id": r["id"], "q": r["question"], "answers": json.loads(r["possible_answers"]), "pop": int(r["s_pop"]), "bin": b}
           for b, B in enumerate(bins) for r in rng.sample(B, 300)]
    json.dump(out, open(path, "w"))
    return out


PROMPT = {"direct": "{q} Answer with a short phrase only.",
          "recall": "{q}\nFirst write two or three facts you know about the subject of the question. Then give the final answer on the last "
                    "line as `Answer: <short phrase>`.",
          "think": "{q} Answer with a short phrase only."}


def final(view, text):
    t = (text or "").strip()
    if view == "recall":
        lines = [l for l in t.splitlines() if l.lower().startswith("answer:")]
        return lines[-1].split(":", 1)[1].strip() if lines else (t.splitlines()[-1] if t else "")
    return t.splitlines()[-1].strip() if t else ""


if __name__ == "__main__":
    from llm import chat
    tag, view, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    Q = questions()
    path = f"{RES}/qa_{tag}_{view}_s{seed}.jsonl"   # tag = model
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()

    def one(q):
        o = chat(PROMPT[view].format(q=q["q"]), think=(view == "think"), max_tokens=4096 if view == "think" else 512, temperature=0.7,
                 seed=seed * 1000 + zlib.crc32(str(q["id"]).encode()) % 997)
        a = final(view, o["text"])
        return {"id": q["id"], "bin": q["bin"], "pop": q["pop"], "answer": a, "correct": any(x.lower() in a.lower() for x in q["answers"]),
                "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, q) for q in Q if q["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = [json.loads(l) for l in open(path)]
    print(tag, view, seed, f"{sum(r['correct'] for r in rows)}/{len(rows)}", flush=True)
