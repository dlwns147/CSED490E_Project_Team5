"""PREREG_DIFF addendum MA-EFF (2026-11-23): one gpt-oss-120b sample per problem at low / medium / high reasoning effort on the
integer-answer problems of MathArena's post-cutoff competitions ($POC_DATA/aime/matharena/ma_problems.json, 155 problems).
usage: POC_BASE_URL=... POC_REASONING_EFFORT=<e> python ma_effort.py run <e> <seed>   |   python ma_effort.py score"""
import json, os, random, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "aime", "matharena")
R = f"{ROOT}/results/x44"
PROMPT = "{p}\n\nPlease reason step by step, and put your final answer within \\boxed{{}}. The answer is an integer."
PROBS = [p for p in json.load(open(f"{D}/ma_problems.json")) if re.fullmatch(r"-?\d+", p["gold"].strip())]


def ans(t):
    m = re.findall(r"\\boxed\{([^{}]*)\}", t or "")
    if not m:
        return None
    a = re.sub(r"[\s,$]|\\[,!;]|\\text\{[^}]*\}", "", m[-1])
    return a.lstrip("+")


def run(e, seed):
    from llm import chat
    out = f"{R}/ma_{os.environ.get('MA_TAG', 'oss120')}{e}_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()

    def one(p):
        o = chat(PROMPT.format(p=p["problem"]), think=True, max_tokens=38000, temperature=1.0,
                 seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        a = ans(o.get("text"))
        return {"id": p["id"], "ans": a, "correct": a is not None and a == p["gold"].strip(), "tok": o.get("out_tokens") or 0,
                "finish": o.get("finish")}
    with ThreadPoolExecutor(48) as ex, open(out, "a") as f:
        for z in ex.map(one, [p for p in PROBS if p["id"] not in done]):
            f.write(json.dumps(z) + "\n"); f.flush()


def score():
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    arms = {}
    for e in ("low", "medium", "high"):
        rows = {}
        for s in (1, 2):
            p = f"{R}/ma_oss120{e}_s{s}.jsonl"
            if os.path.exists(p):
                for l in open(p):
                    z = json.loads(l); rows.setdefault(z["id"], []).append(U(z["correct"], z["tok"]))
        if rows:
            arms[e] = {i: sum(v) / len(v) for i, v in rows.items()}
    ids = sorted(set.intersection(*(set(a) for a in arms.values()))) if arms else []
    for e, a in arms.items():
        print(f"{e}: n={len(ids)} utility {sum(a[i] for i in ids)/max(1,len(ids)):.2f}")
    for a, b in (("medium", "high"), ("low", "medium"), ("low", "high")):
        if a in arms and b in arms:
            d = [arms[a][i] - arms[b][i] for i in ids]; rng = random.Random(1)
            bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
            print(f"{a} - {b}: {sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}]")


if __name__ == "__main__":
    run(sys.argv[2], int(sys.argv[3])) if sys.argv[1] == "run" else score()
