"""GRLK (docs/prereg/PREREG_GRLK.md): pass@k of the quick grid translation's first round, base Qwen3-8B against the GRL-trained translator
(PREREG_GRL), to tell sharpening from new coverage (Yue et al. 2504.13837: RLVR wins at small k, the base at large k). Per puzzle, N programs
are sampled with gtr's first-round prompt and settings (no thinking, temperature 0.7, top_p 0.95; gp_train.prompt), each graded as GRL's
reward (gp_train.grade: solver count 1 and the gold grid under scoring v2). The server's model "local" is the base model or the fold's adapter.
usage: python gp_passk.py <tag> [--ids <file>] [--n 128] [--chunk 32]   -> results/gpk_<tag>.jsonl, one row per puzzle: {id, set, n, right, count1}
       python gp_passk.py --report <base tag>[,...] <trained tag>[,...]   (unbiased pass@k for k = 1..N, differences with a 95% bootstrap
       over puzzles; on the puzzles in both)"""
import json, math, os, random, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gp_train import CAP, grade, prompt, puzzles  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
BASE_URL = os.environ.get("POC_BASE_URL", "http://127.0.0.1:30000/v1")


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def sample(msgs, n, seed):
    body = {"model": "local", "messages": msgs, "n": n, "temperature": 0.7, "top_p": 0.95, "max_tokens": CAP, "seed": seed,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return [c["message"]["content"] or "" for c in json.loads(r.read())["choices"]]


def passk(n, c, k):   # unbiased estimator (Chen et al. 2021)
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


def report(base, trained):
    rows = lambda t: {r["id"]: r for r in map(json.loads, open(f"{RES}/gpk_{t}.jsonl"))}
    B, T = {}, {}
    for t in base.split(","):
        B.update(rows(t))
    for t in trained.split(","):
        T.update(rows(t))
    for s, nm in (("gridpuzzle", "GridPuzzle"), ("lgp", "Mitra-Baral")):
        ids = sorted(i for i in T if i in B and T[i]["set"] == s)
        if not ids:
            continue
        n = min(min(B[i]["n"], T[i]["n"]) for i in ids)
        print(f"== {nm}: {len(ids)} puzzles, {n} samples each")
        rng = random.Random(0)
        boots = [[rng.choice(ids) for _ in ids] for _ in range(2000)]
        k = 1
        while k <= n:
            pb = {i: passk(B[i]["n"], B[i]["right"], k) for i in ids}
            pt = {i: passk(T[i]["n"], T[i]["right"], k) for i in ids}
            d = sorted(sum(pt[i] - pb[i] for i in b) / len(b) for b in boots)
            print(f"  pass@{k:<4} base {100 * sum(pb.values()) / len(ids):5.1f}%  trained {100 * sum(pt.values()) / len(ids):5.1f}%  "
                  f"trained - base {100 * sum(pt[i] - pb[i] for i in ids) / len(ids):+5.1f} [{100 * d[50]:+.1f}, {100 * d[1949]:+.1f}]")
            k *= 2
        never = [i for i in ids if B[i]["right"] == 0]
        print(f"  base never right in {n}: {len(never)} puzzles; trained right at least once on {sum(T[i]['right'] > 0 for i in never)}; "
              f"base right at least once but trained never: {sum(B[i]['right'] > 0 and T[i]['right'] == 0 for i in ids)}")
        cb = sum(B[i]["count1"] for i in ids); ct = sum(T[i]["count1"] for i in ids)
        print(f"  count-1 precision per sample: base {100 * sum(B[i]['right'] for i in ids) / max(1, cb):.1f}%  "
              f"trained {100 * sum(T[i]['right'] for i in ids) / max(1, ct):.1f}%")


def main():
    if "--report" in sys.argv:
        i = sys.argv.index("--report")
        return report(sys.argv[i + 1], sys.argv[i + 2])
    tag, N, C = sys.argv[1], arg("--n", 128), arg("--chunk", 32)
    P = puzzles()
    if "--ids" in sys.argv:
        keep = set(open(sys.argv[sys.argv.index("--ids") + 1]).read().split())
        P = [r for r in P if r["id"] in keep]
    path = f"{RES}/gpk_{tag}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
    P = [r for r in P if r["id"] not in done]
    out = open(path, "a")
    gx = ThreadPoolExecutor(int(os.environ.get("GPK_WORKERS", 24)))

    def one(r):
        msgs = [{"role": "user", "content": prompt(r)}]
        sd = int(r["id"].split("-")[1]) * 1009
        texts = [t for j in range(0, N, C) for t in sample(msgs, min(C, N - j), sd + j)]
        g = list(gx.map(lambda t: grade(t, r), texts))
        return {"id": r["id"], "set": r["set"], "n": len(g), "right": sum(ok for _, ok in g), "count1": sum(c == 1 for c, _ in g)}
    with ThreadPoolExecutor(8) as ex:
        for k, row in enumerate(ex.map(one, P)):
            out.write(json.dumps(row) + "\n"); out.flush()
            if k % 20 == 0:
                print(tag, k + 1, "/", len(P), row, flush=True)
    print(tag, "done", flush=True)


if __name__ == "__main__":
    main()
