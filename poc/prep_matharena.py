"""Slim MathArena *_outputs parquet files ($POC_DATA/aime/matharena/<comp>.parquet, downloaded from huggingface.co/datasets/MathArena)
into one row per (competition, problem, model, run): parsed answer, correct, output tokens. -> $POC_DATA/aime/matharena/ma_rows.jsonl
and ma_problems.json. The full messages are dropped; the downloaded parquet files are temporary and are deleted at the end."""
import glob, json, os
import pyarrow.parquet as pq   # the image has no parquet engine: pip install --target <tmp dir> pyarrow, run with PYTHONPATH=<tmp dir>, delete the dir afterwards
D = os.path.join(os.environ.get("POC_DATA", "/NAS/SJ/POSTECH/nlp_data"), "aime", "matharena")
probs = {}
with open(f"{D}/ma_rows.jsonl", "w") as f:
    for p in sorted(glob.glob(f"{D}/*.parquet")):
        comp = os.path.basename(p)[:-8]
        rows = pq.read_table(p, columns=["problem_idx", "problem", "model_name", "model_config", "idx_answer", "output_tokens",
                                         "gold_answer", "parsed_answer", "correct"]).to_pylist()
        for r in rows:
            key = f"{comp}|{r['problem_idx']}"
            probs.setdefault(key, {"id": key, "comp": comp, "problem": r["problem"], "gold": str(r["gold_answer"])})
            f.write(json.dumps({"id": key, "model": r["model_name"], "config": r["model_config"], "run": int(r["idx_answer"] or 0),
                                "ans": None if r["parsed_answer"] is None else str(r["parsed_answer"]), "correct": bool(r["correct"]),
                                "tok": int(r["output_tokens"] or 0)}) + "\n")
        print(comp, len(rows), len({r["problem_idx"] for r in rows}), len({r["model_name"] for r in rows}), flush=True)
json.dump(list(probs.values()), open(f"{D}/ma_problems.json", "w"))
for p in glob.glob(f"{D}/*.parquet"):   # temporary inputs: removed once the slim rows are written
    os.remove(p)
