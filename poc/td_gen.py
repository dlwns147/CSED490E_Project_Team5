"""TD (docs/prereg/PREREG_TD.md): training data for the quick program from two sources on the same OptMATH-Train problems — the first N of
WP-RL's training order ($POC_DATA/optmath_train/wp_train_items.jsonl, shuffled with Random(0) as poc/wp_train.py does). Per problem, the
held-out sets' cheap prompt (run_nlopt.P_FREE):
  quick  8 non-thinking programs (T 0.7, top-p 0.95, 1,536 tokens: WP-RL's rollouts);
  sb     thinking cut at 2,000 tokens (budget forcing, as the default's first step), then the program;
  t      full thinking (16,000 tokens), only where sb's program is not right (labels are used in training, as by RL).
Each program runs in the sandbox as run_nlopt does (60 s, 4 GB) and is graded against the gold optimum (run_nlopt.correct).
Rows: $POC_DATA/optmath_train/td/td_<tag>_p<j>.jsonl = {id, gold, quick: [{code, pred, runs, right, tok}], sb: {...}, t: {...} | null}
(code only, not the text: the SFT targets are the programs; poc/td_build.py). Resumes.
usage: TD_SUBSET=j/k [TD_FROM=0] [TD_ARMS=quick] POC_BASE_URL=... python td_gen.py <tag> [N 2000]"""
import json, os, random, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, client, last_block  # noqa: E402
from run_geo_cross import budget_chat  # noqa: E402
from run_nlopt import P_FREE, correct, value_of, _rows  # noqa: E402
from sandbox import run_python  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
CAP, G = 1536, 8


def grade(text, gold, tok):
    code = last_block(text or "", ("python", "py", "python3"))
    if not code:
        return {"code": None, "pred": None, "runs": False, "right": False, "tok": tok}
    r = run_python(code, "", timeout=60, mem_bytes=4 << 30, cpu_s=3600)
    lines = [l for l in (r.stdout if r.status == "ok" else "").strip().splitlines() if l.strip()]
    pred = value_of(lines[-1]) if lines else None
    return {"code": code, "pred": pred, "runs": pred is not None, "right": correct(pred, gold), "tok": tok}


def one(p):
    q = P_FREE.format(q=p["q"])
    sd = zlib.crc32(p["id"].encode()) % (1 << 30)
    r = client.chat.completions.create(model="local", messages=[{"role": "user", "content": q}], n=G, temperature=0.7, top_p=0.95,
                                       max_tokens=CAP, seed=sd, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    quick = [grade(c.message.content, p["gold"], None) for c in r.choices]
    per = r.usage.completion_tokens / G
    for x in quick:
        x["tok"] = round(per)   # vLLM reports the total over the n samples
    if os.environ.get("TD_ARMS") == "quick":   # RFT data only (PREREG_TD.md addendum RF)
        return {"id": p["id"], "gold": p["gold"], "quick": quick, "sb": None, "t": None}
    o = budget_chat(q, 2000, max_tokens=8192, temperature=0.7, seed=sd)
    sb = dict(grade(o["text"], p["gold"], o["out_tokens"]), think=o.get("think_tokens"))
    t = None
    if not sb["right"]:
        o = chat(q, think=True, max_tokens=16000, temperature=0.7, seed=sd)
        t = grade(o["text"], p["gold"], o["out_tokens"])
    return {"id": p["id"], "gold": p["gold"], "quick": quick, "sb": sb, "t": t}


def main():
    tag = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    items = [json.loads(l) for l in open(f"{DATA}/optmath_train/wp_train_items.jsonl")]
    random.Random(0).shuffle(items)
    items = items[int(os.environ.get("TD_FROM", 0)):n]   # TD_FROM: skip the first problems of the order (addendum RF: 2000 4000)
    j, k = map(int, os.environ.get("TD_SUBSET", "0/1").split("/"))
    items = items[j::k]
    os.makedirs(f"{DATA}/optmath_train/td", exist_ok=True)
    path = f"{DATA}/optmath_train/td/td_{tag}_p{j}.jsonl"
    done = {r["id"] for r in _rows(path)}
    with ThreadPoolExecutor(int(os.environ.get("TD_THREADS", 32))) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in items if p["id"] not in done]):
            try:
                f.write(json.dumps(fu.result()) + "\n"); f.flush()
            except Exception as e:
                print(tag, j, "request failed, no row:", repr(e)[:200], flush=True)
    R = _rows(path)
    qr = sum(any(x["right"] for x in r["quick"]) for r in R)
    tr = sum(bool(r["sb"] and r["sb"]["right"]) or bool(r["t"] and r["t"]["right"]) for r in R)
    print(tag, j, f"{len(R)} problems: quick right in any of {G} {qr}, thinking right {tr}", flush=True)


if __name__ == "__main__":
    main()
