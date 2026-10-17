"""M3 (results/PREREG_M2_M4.md): behavioural per-helper probing. For each instance and each offered helper h, the model writes one program
with only h (+ deps) offered; h is kept if that program is consistent on the metamorphic copies of the given instance (label-free).
Outputs: a keep-JSON for run_geo_cross.py --keep_json (final program with the kept helpers), and a direct variant "MR-select over the
no-helper draft and the per-helper programs" (no extra generation), with tokens per instance.
usage: POC_BASE_URL=... python helper_probe.py <draft_tag> <out_tag> <tasks> <n_inst> <seed> [K=8]"""
import json, os, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import render_names, toolbox, with_deps  # noqa: E402
from llm import chat, last_block  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_mr import mr_check  # noqa: E402
from sandbox import run_python  # noqa: E402
from steer_filter import SIZES, fix_tb, prompt_txt  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"


def all_correct(code, task, V):
    if not code:
        return False
    for x in V.values():
        r = run_python(code, render(task, x)[1], timeout=10)
        out = (r.stdout.strip().split() or [None])[-1] if r.status == "ok" else None
        if out is None or out.lower() != answer(task, x):
            return False
    return True


def main():
    draft_tag, out_tag, tasks, n_inst, seed = sys.argv[1], sys.argv[2], sys.argv[3].split(","), int(sys.argv[4]), int(sys.argv[5])
    K = int(sys.argv[6]) if len(sys.argv) > 6 else 8
    drafts = {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f"{RES}/geocross_{draft_tag}.jsonl"))}
    jobs = [(t, n, i) for t in tasks for n in SIZES[t] for i in range(n_inst)]

    def one(job):
        task, n, i = job
        rng = random.Random(f"{task}-{n}-{i}")
        V = variants(task, base_instance(task, n, rng), rng)
        q, _, fmt = render(task, V["identity"])
        tb, _ = toolbox(task, K, "related", random.Random(f"{task}-{n}-{i}-tb"))
        items = re.findall(r"^def (\w+)\(", tb, re.M)
        sd = seed * 1000 + i + 100 * n
        progs, tok = {}, 0
        for j, h in enumerate(items):
            o = chat(prompt_txt(q, fmt, fix_tb(task, render_names(with_deps([h])))), think=False, max_tokens=4096, temperature=0.7, seed=sd + 31 * (j + 1))
            progs[h] = last_block(o["text"], ("python", "py", "python3")); tok += o["out_tokens"] or 0
        cons = {}
        for h, c in progs.items():
            base, bad = mr_check(c, task, V) if c else (None, ["x"])
            cons[h] = (base, base is not None and not bad)
        d0 = drafts.get(job, {}).get("code")
        b0, bad0 = mr_check(d0, task, V) if d0 else (None, ["x"])
        cands = [(h, cons[h][0]) for h in items if cons[h][1]] + ([("__draft__", b0)] if b0 is not None and not bad0 else [])
        if cands:
            vote = Counter(b for _, b in cands).most_common(1)[0][0]
            pick = next(h for h, b in cands if b == vote)
            sel_ok = all_correct(d0 if pick == "__draft__" else progs[pick], task, V)
        else:
            sel_ok = False
        return f"{task}-{n}-{i}", [h for h in items if cons[h][1]], items, tok, sel_ok

    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(one, jobs))
    json.dump({k: kept for k, kept, _, _, _ in res}, open(f"{RES}/m3_keep_{out_tag}.json", "w"))
    json.dump([{"key": k, "kept": kept, "items": it, "probe_tokens": tok, "mrselect_ok": ok} for k, kept, it, tok, ok in res],
              open(f"{RES}/m3_probe_{out_tag}.json", "w"))
    n = len(res)
    print(f"{out_tag}: kept {sum(len(r[1]) for r in res) / n:.2f} of {sum(len(r[2]) for r in res) / n:.2f} helpers; probe tokens "
          f"{sum(r[3] for r in res) / n:.0f}/instance; MR-select over draft + per-helper programs {sum(r[4] for r in res)}/{n}")


if __name__ == "__main__":
    main()
