"""PoC G2b — cross-variant execution of LLM-written geometry code (Spatter-style metamorphic relations for LLM code).

For each base instance the model writes ONE program from the identity prompt; we then run that same program on all
8 variants. Failure taxonomy per program:
  correct_all    : right on every variant
  logic          : wrong on the identity instance (and usually everywhere)
  degen_only     : right on all non-degenerate variants, wrong on the degenerate one (collinear/duplicate/vertex-ray/touch)
  big_only       : right except on the ~1e9-offset variant (float precision / overflow)
  transform_only : right on identity but wrong on some rigid/scale/permute variant (non-invariant code)
  crash          : no code / runtime error / timeout on identity
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat, last_block, strip_think  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


def classify(res):
    if res["identity"] is None:
        return "crash"
    if not res["identity"]:
        return "logic"
    bad = [v for v, ok in res.items() if not ok]
    if not bad:
        return "correct_all"
    if bad == ["degen"]:
        return "degen_only"
    if bad == ["big"]:
        return "big_only"
    if set(bad) <= {"degen", "big"}:
        return "degen+big"
    return "transform_only"


PRIMS = """You may (and should) use these tested, exact integer predicates; copy them into your program unchanged:
```python
def orient(a, b, c):            # >0 left turn, <0 right turn, 0 collinear (exact for integers)
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
def on_segment(a, b, p):        # p lies on the closed segment ab
    return orient(a, b, p) == 0 and min(a[0],b[0]) <= p[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= p[1] <= max(a[1],b[1])
def segments_intersect(a, b, c, d):   # closed segments ab and cd share at least one point
    d1, d2, d3, d4 = orient(c,d,a), orient(c,d,b), orient(a,b,c), orient(a,b,d)
    if ((d1>0 and d2<0) or (d1<0 and d2>0)) and ((d3>0 and d4<0) or (d3<0 and d4>0)): return True
    return on_segment(c,d,a) or on_segment(c,d,b) or on_segment(a,b,c) or on_segment(a,b,d)
def point_in_polygon(poly, q):  # 'inside' / 'outside' / 'boundary' (winding number, exact)
    wn = 0
    for i in range(len(poly)):
        a, b = poly[i], poly[(i+1) % len(poly)]
        if on_segment(a, b, q): return 'boundary'
        if a[1] <= q[1]:
            if b[1] > q[1] and orient(a, b, q) > 0: wn += 1
        elif b[1] <= q[1] and orient(a, b, q) < 0: wn -= 1
    return 'inside' if wn != 0 else 'outside'
```"""

NEED = {"hull": ["orient"], "pip": ["orient", "on_segment", "point_in_polygon"],
        "segs": ["orient", "on_segment", "segments_intersect"], "area2": [], "close": [],
        "overlap": ["orient", "on_segment", "segments_intersect", "point_in_polygon"], "lattice": [], "rectunion": [], "clip": ["orient"]}


ALGO_HINT = {   # RAG-style TEXT hints (an algorithm description instead of helper code); --algo_hint
    "hull": "Hint (algorithm): Andrew's monotone chain. Sort the distinct points by (x, y); build the lower hull left to right and the upper hull "
            "right to left, popping the last point while the cross product of the last two points and the new point is <= 0 (this also drops "
            "collinear points); the hull is lower[:-1] + upper[:-1].",
    "lattice": "Hint (algorithm): Pick's theorem. For a simple polygon with integer vertices, A = I + B/2 - 1, where A is the area (use the exact "
               "integer shoelace sum S = 2A, taking its absolute value), B is the number of lattice points on the boundary (sum over edges of "
               "gcd(|dx|, |dy|)), and I the number strictly inside: I = (|S| - B + 2) / 2.",
    "clip": "Hint (algorithm): Sutherland-Hodgman clipping. Orient both polygons counter-clockwise; clip A successively by each edge of B "
            "(keep points on the left side, add the intersection point where an edge of the current polygon crosses the clipping line), using "
            "fractions.Fraction for exact coordinates; twice the area of the result is the absolute shoelace sum; print it with Fraction's p/q.",
    "rectunion": "Hint (algorithm): sweep line. Collect the distinct x-coordinates of all rectangle sides and sort them. For each slab between "
                 "consecutive x-values, take the y-intervals of the rectangles that cover the whole slab, sort and merge overlapping intervals, "
                 "and add (total merged length) x (slab width).",
}


ALGO_LIB = [   # a small "textbook" library for retrieval of algorithm descriptions (--hint_retrieve): right entries + plausible near-misses
    ("Convex hull: Andrew's monotone chain (count hull vertices, collinear points excluded)", ALGO_HINT["hull"]),
    ("Convex hull: Graham scan", "Pick the lowest point, sort the other points by polar angle around it (ties by distance), then scan with a "
     "stack, popping while the last two stack points and the new point do not make a left turn."),
    ("Convex hull: gift wrapping (Jarvis march)", "Start from the leftmost point and repeatedly pick the point such that all other points are "
     "to the right of the line from the current point to it, until returning to the start."),
    ("Lattice points inside a polygon: Pick's theorem", ALGO_HINT["lattice"]),
    ("Point in polygon: ray casting", "Cast a horizontal ray from the query point and count how many polygon edges it crosses; an odd count "
     "means inside. Treat vertices on the ray with a half-open rule."),
    ("Point in polygon: winding number", "Sum the signed angle (or signed crossings) of the polygon around the query point; non-zero means inside."),
    ("Polygon area: shoelace formula", "Twice the signed area is sum over edges of x_i*y_{i+1} - x_{i+1}*y_i; take the absolute value."),
    ("Area of a union of rectangles: sweep line", ALGO_HINT["rectunion"]),
    ("Area of a union of rectangles: inclusion-exclusion", "Add the areas of all rectangles, subtract the areas of all pairwise intersections, "
     "add back triple intersections, and so on over all subsets."),
    ("Segment intersection test", "Two segments intersect iff the orientations of each segment's endpoints with respect to the other differ, "
     "or an endpoint lies on the other segment (collinear case)."),
    ("Closest pair of points: divide and conquer", "Sort by x, split, solve both halves, then check points within distance d of the split line "
     "sorted by y, comparing each with the next 7."),
]


def retrieve_hint(q, k=1):
    import math as _m
    tok = lambda t: re.findall(r"[a-z]+", t.lower())
    D = [tok(a + " " + b) for a, b in ALGO_LIB]; N = len(D); avg = sum(map(len, D)) / N
    df = {}
    for d in D:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    qs = set(tok(q)); sc = []
    for (title, text), d in zip(ALGO_LIB, D):
        v = sum(_m.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * d.count(w) * 2.5 / (d.count(w) + 1.5 * (0.25 + 0.75 * len(d) / avg))
                for w in qs if w in d)
        sc.append((v, title, text))
    sc.sort(key=lambda x: -x[0])
    return sc[:k]


def budget_chat(prompt, budget, think=False, max_tokens=4096, temperature=0.7, seed=None, cut_note="I will now write the program.", system=None):
    """budget forcing (s1-style) for Qwen3: think for at most `budget` tokens, then force </think> and generate the answer.
    Uses the raw completions endpoint with the Qwen3 chat format; budget=0 means an empty think block (= thinking off).
    cut_note: what the cut think says it does next (IF-1: "I will now write the response."); system: a system turn (TC-1: the tool docs)."""
    from llm import client
    head = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n"
    if system:
        head = f"<|im_start|>system\n{system}<|im_end|>\n" + head
    elif os.environ.get("POC_RAW_SYSTEM"):   # HO-N4: Nemotron-3-Nano's template always opens with an empty system turn
        head = "<|im_start|>system\n<|im_end|>\n" + head
    think_txt, used = "", 0
    if budget > 0:
        r = client.completions.create(model="local", prompt=head, max_tokens=budget, temperature=temperature,
                                      top_p=0.95 if temperature > 0 else 1.0, seed=seed, stop=["</think>"])
        think_txt, used, cut = r.choices[0].text, r.usage.completion_tokens, r.choices[0].finish_reason == "length"
    cont = head + think_txt + (f"\n\nTime is up; {cut_note}\n" if budget > 0 and cut else "") + "\n</think>\n\n"
    r2 = client.completions.create(model="local", prompt=cont, max_tokens=max_tokens, temperature=temperature,
                                   top_p=0.95 if temperature > 0 else 1.0, seed=seed, stop=["<|im_end|>"])
    return {"text": r2.choices[0].text, "finish": r2.choices[0].finish_reason, "out_tokens": used + r2.usage.completion_tokens,
            "think_tokens": used}


def seed_budget_chat(prompt, budget, max_tokens=4096, temperature=0.7, seed=None):
    """HO-SEED: budget forcing for Seed-OSS (POC_SEED set), as budget_chat: its chat format rendered by hand (one user turn, no budget
    system turn = unlimited thinking), the think cut at `budget` tokens, </seed:think> forced, then the answer. Thinking sampling
    (POC_THINK_SAMPLING) applies to both calls, as to its native-budget and full thinks."""
    from llm import client, _TS
    t, tp = _TS.get("temperature", temperature), _TS.get("top_p", 0.95 if temperature > 0 else 1.0)
    head = f"<seed:bos>user\n{prompt}<seed:eos><seed:bos>assistant\n<seed:think>"
    r = client.completions.create(model="local", prompt=head, max_tokens=budget, temperature=t, top_p=tp, seed=seed, stop=["</seed:think>"])
    think_txt, used, cut = r.choices[0].text, r.usage.completion_tokens, r.choices[0].finish_reason == "length"
    cont = head + think_txt + ("\n\nTime is up; I will now write the program." if cut else "") + "</seed:think>"
    r2 = client.completions.create(model="local", prompt=cont, max_tokens=max_tokens, temperature=t, top_p=tp, seed=seed)
    return {"text": r2.choices[0].text, "finish": r2.choices[0].finish_reason, "out_tokens": used + r2.usage.completion_tokens,
            "think_tokens": used}


def harmony_budget_chat(prompt, budget, max_tokens=4096, temperature=0.7, seed=None):
    """HO-OSB: budget forcing for gpt-oss (POC_HARMONY set). The prompt is the model's chat template rendered by hand (one user turn,
    no tools; the client venv has no transformers) at POC_HARMONY_EFFORT (default medium); the analysis channel runs for at most
    `budget` tokens (<|end|>, id 200007, ends it), then the final channel is forced and the answer generated."""
    import time
    from llm import client
    head = ("<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2024-06\n"
            f"Current date: {time.strftime('%Y-%m-%d')}\n\nReasoning: {os.environ.get('POC_HARMONY_EFFORT', 'medium')}\n\n"
            "# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|>"
            f"<|start|>user<|message|>{prompt}<|end|><|start|>assistant<|channel|>analysis<|message|>")
    tp = 0.95 if temperature > 0 else 1.0
    r = client.completions.create(model="local", prompt=head, max_tokens=budget, temperature=temperature, top_p=tp, seed=seed,
                                  extra_body={"stop_token_ids": [200007]})
    think_txt, used, cut = r.choices[0].text, r.usage.completion_tokens, r.choices[0].finish_reason == "length"
    cont = head + think_txt + ("\n\nTime is up; I will now write the program." if cut else "") + "<|end|><|start|>assistant<|channel|>final<|message|>"
    r2 = client.completions.create(model="local", prompt=cont, max_tokens=max_tokens, temperature=temperature, top_p=tp, seed=seed)
    return {"text": r2.choices[0].text, "finish": r2.choices[0].finish_reason, "out_tokens": used + r2.usage.completion_tokens,
            "think_tokens": used}


def prims(task, a):
    if not a.prims_task:
        return PRIMS
    if not NEED[task]:
        return ""
    head, body = PRIMS.split("```python\n")
    defs = body.rstrip("`").split("def ")[1:]
    keep = ["def " + d for d in defs if d.split("(")[0] in NEED[task]]
    return head + "```python\n" + "".join(keep).rstrip() + "\n```"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--n_inst", type=int, default=10)
    ap.add_argument("--robust_hint", action="store_true", help="T3: ask for exact integer arithmetic and degenerate-case handling")
    ap.add_argument("--primitives", action="store_true", help="S4: provide tested exact geometric predicates to call")
    ap.add_argument("--prims_task", action="store_true", help="S4b: only the predicates this task needs (hull: orient; "
                    "pip/segs: their predicate + helpers; area2/close: none)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=None, help="sampling seed (used with --temperature > 0)")
    ap.add_argument("--distract", type=int, default=-1, help="S4d: task-matched helpers + K distractor helpers (dose-response)")
    ap.add_argument("--autoscope", action="store_true", help="S5: two-stage; the model picks helpers from a catalog (same pool as "
                    "--distract K), then gets only the chosen ones in full")
    ap.add_argument("--tasks", default="", help="comma list; default the five original tasks. Held-out: convex,tri")
    ap.add_argument("--autoscope_mode", default="pick", choices=["pick", "pointwise", "plan", "lexical"])
    ap.add_argument("--tb_usage", action="store_true", help="state the helper API contract: points are (x, y) tuples, with example calls")
    ap.add_argument("--inst_prefix", default="", help="E5: prefix for the instance/toolbox RNG keys (e.g. 'train-' = instances disjoint from eval)")
    ap.add_argument("--save_prompt", action="store_true", help="store the exact prompt in each row (E5 SFT data)")
    ap.add_argument("--fast_fail", action="store_true", help="H1: stop running the other 7 copies once the original input fails (saves CPU on large inputs)")
    ap.add_argument("--auto_contract", action="store_true", help="M2: insert the harness-probed behaviour statement (results/contracts.json) into helpers")
    ap.add_argument("--algo_first_free", action="store_true", help="M4 baseline (De-Hallucinator-style): draft first, then rewrite with helpers, no keep-the-algorithm instruction")
    ap.add_argument("--algo_first", action="store_true", help="M4: write a program without helpers first, then refactor it to use the helpers")
    ap.add_argument("--keep_json", default="", help="M1: JSON {task-n-inst: [kept helper names]}; the offered toolbox is filtered to these (+ deps)")
    ap.add_argument("--api_only_note", action="store_true", help="L2: state that geomlib contains exactly the listed functions")
    ap.add_argument("--tb_api", action="store_true", help="L1: helpers as an importable module `geomlib`, prompt shows only its API (signature + doc)")
    ap.add_argument("--scope_note", action="store_true", help="B3: one sentence on helper scope after the toolbox (cf. 2609.14157)")
    ap.add_argument("--s2a", action="store_true", help="B3: System 2 Attention: the model first rewrites the prompt keeping only what is relevant")
    ap.add_argument("--incircle_comment", default="", help="B3: replace the comment of the signed in_circle helper by this text (DRAFT docs)")
    ap.add_argument("--brute", action="store_true", help="E3b: ask for the simplest brute-force program (a differential-testing reference)")
    ap.add_argument("--show_stdin", action="store_true", help="append this instance's literal stdin to the prompt (format example, cf. run_co)")
    ap.add_argument("--logprobs_topk", type=int, default=0, help="B1: also store DeepConf token confidence from the top-k log-probs")
    ap.add_argument("--logprobs", action="store_true", help="store the raw log-prob of every sampled token (confidence analysis)")
    ap.add_argument("--self_hint", action="store_true", help="two-step: the model first names its algorithm (1-2 sentences), then codes with it")
    ap.add_argument("--hint_retrieve", action="store_true", help="BM25 top-1 algorithm description from ALGO_LIB appended to the prompt")
    ap.add_argument("--algo_hint", action="store_true", help="append a short text description of the standard algorithm (hull/lattice/rectunion)")
    ap.add_argument("--distract_set", default="", help='E4: JSON {task: [helper, ...]} fixed distractor sets (use with --distract 0)')
    ap.add_argument("--incircle", default="signed", choices=["signed", "doc", "fixed"],
                    help="E2 F2-replication: the needed in_circle helper with its counter-clockwise contract terse / spelled out / removed")
    ap.add_argument("--area_helper", default="signed", choices=["signed", "signed_doc", "abs"],
                    help="T7: polygon_area2 as given (signed), with an explicit sign warning, or returning abs()")
    ap.add_argument("--tb_head", default="should", choices=["should", "may", "prelude", "neutral"],
                    help="toolbox header: 'should use' / 'use only if needed' / 'prelude' (helpers pre-defined at execution: removes copy-failure NameErrors)")
    ap.add_argument("--distract_kind", default="related", choices=["related", "unrelated"])
    ap.add_argument("--prompt_variant", type=int, default=0, choices=[0, 1, 2], help="review item 6: paraphrased instruction templates")
    ap.add_argument("--size_mult", type=int, default=1, help="review item 3: multiply every instance size (e.g. 5 -> hull 50/100 points)")
    ap.add_argument("--think_budget", type=int, default=-1, help="budget forcing: think at most B tokens (Qwen3 raw format), then answer; -1 = off")
    ap.add_argument("--stdlib", action="store_true", help="state the environment fact: only the Python standard library is available")
    ap.add_argument("--fmt_after", action="store_true", help="S4c: restate the stdin format after the predicate block")
    ap.add_argument("--resume", action="store_true", help="append to an existing result file, skipping finished instances")
    a = ap.parse_args()
    sizes = {"hull": (10, 20), "area2": (8, 14), "pip": (8, 14), "segs": (6, 10), "close": (10, 20), "convex": (8, 14), "tri": (10, 20), "overlap": (8, 14), "lattice": (8, 14), "rectunion": (5, 9), "clip": (6, 10),
             "delaunay": (8, 12), "diameter": (12, 24), "hullL": (2000, 20000), "closeL": (2000, 20000), "diamL": (2000, 20000)}
    if not a.tasks:
        sizes = {t: sizes[t] for t in ("hull", "area2", "pip", "segs", "close")}
    else:
        sizes = {t: sizes[t] for t in a.tasks.split(",")}
    if a.size_mult > 1:
        sizes = {t: tuple(v * a.size_mult for v in ns) for t, ns in sizes.items()}
    jobs = []
    for task, ns in sizes.items():
        for n in ns:
            for i in range(a.n_inst):
                rng = random.Random(f"{a.inst_prefix}{task}-{n}-{i}")
                inst = base_instance(task, n, rng)
                jobs.append((task, n, i, variants(task, inst, rng)))

    def run(j):
        task, n, i, V = j
        q, _, fmt = render(task, V["identity"])
        tb, dis = ("", [])
        if a.distract >= 0:
            from geo_distractors import toolbox
            tb, dis = toolbox(task, a.distract, a.distract_kind, random.Random(f"{a.inst_prefix}{task}-{n}-{i}-tb"), a.tb_head,
                              fixed=json.loads(a.distract_set).get(task) if a.distract_set else None)
            if a.keep_json and tb:   # M1: keep only the helpers the steering-score filter kept (original order, deps added)
                from geo_distractors import render_names, with_deps
                kept = set(with_deps(json.load(open(a.keep_json)).get(f"{task}-{n}-{i}", [])))
                order = re.findall(r"^def (\w+)\(", tb, re.M)
                tb = render_names([x for x in order if x in kept], a.tb_head) if kept else ""
                dis = [d for d in dis if d in kept]
            if a.tb_api and tb:   # L1: describe the offered helpers as a library API; the module itself is injected at execution
                from geo_distractors import catalog
                api_src = "\n".join(re.findall(r"```python\n(.*?)```", tb, re.S)) + "\n"
                names = re.findall(r"^def (\w+)\(", api_src, re.M)
                tb = ("The Python module `geomlib` is installed in the environment; import what you need from it (for example "
                      "`from geomlib import " + names[0] + "`). Its API (all coordinates are integers; points are (x, y) tuples):\n" + catalog(names)
                      + ("\nThe module contains exactly these functions and nothing else; anything else you need, write yourself."
                         if a.api_only_note else ""))
            if "in_circle" in tb and a.incircle_comment:   # B3: DRAFT-style rewritten doc for the (signed) helper
                from geo_distractors import INCIRCLE_VARIANTS
                old = "# exact in-circle test for a counter-clockwise triangle abc: > 0 inside, 0 on, < 0 outside its circumcircle"
                assert old in tb
                tb = tb.replace(old, "# " + a.incircle_comment.strip().lstrip("#").strip().replace("\n", " "))
            if "in_circle" in tb and a.incircle != "signed":   # E2: swap in the doc / fixed version of the needed helper
                from geo_distractors import INCIRCLE_VARIANTS
                assert INCIRCLE_VARIANTS["signed"] in tb
                tb = tb.replace(INCIRCLE_VARIANTS["signed"], INCIRCLE_VARIANTS[a.incircle])
            if a.area_helper != "signed":   # T7 causal test of the signed-area trap: same helper, clearer contract / unsigned version
                sig = "def polygon_area2(poly):        # twice the signed area (shoelace, exact)\n    return sum("
                assert sig in tb or "polygon_area2" not in tb
                tb = tb.replace(sig, {"signed_doc": "def polygon_area2(poly):        # twice the SIGNED area (shoelace, exact): NEGATIVE for "
                                                    "clockwise vertex order; use abs() for the area\n    return sum(",
                                      "abs": "def polygon_area2(poly):        # twice the area (shoelace, exact, always >= 0)\n    return abs(sum("}[a.area_helper])
                if a.area_helper == "abs":
                    tb = tb.replace("for i in range(len(poly)))\n", "for i in range(len(poly))))\n", 1)
        if a.auto_contract and tb:   # M2: verified behaviour statements from harness-side metamorphic probing
            C_ = json.load(open(f"{ROOT}/results/contracts.json"))
            lines = tb.split("\n")
            for name, info in C_.items():
                if info.get("statement"):
                    for li, l in enumerate(lines):
                        if l.startswith(f"def {name}("):
                            lines.insert(li + 1, "    # " + info["statement"]); break
            tb = "\n".join(lines)
        chosen, offered = None, None
        if a.autoscope:   # S5: let the model scope its own toolbox from the same pool
            from geo_distractors import NEED as GNEED, catalog, render_names, with_deps
            offered = re.findall(r"^def (\w+)\(", tb, re.M)
            sd_ = None if a.seed is None else a.seed * 1000 + i + 100 * n + 7
            plan = ""
            if a.autoscope_mode == "plan":   # S5c: plan the algorithm BEFORE seeing any helper, then select against the plan
                o0 = chat(f"{q}\n\nDo not write code yet. In at most 6 short numbered steps, describe the algorithm you will "
                          f"implement for this input format: {fmt}.", think=a.think, max_tokens=1024, temperature=a.temperature, seed=sd_)
                plan = strip_think(o0["text"] or "")[-1500:]
            if a.autoscope_mode == "lexical":   # E3: retrieval baseline, top-1 helper by IDF-weighted word overlap (task text vs name + doc)
                import math
                toks = lambda t: [w for w in re.split(r"[^a-z0-9]+", t.lower().replace("_", " ")) if len(w) > 2]
                docs = {h: toks(line) for h, line in zip(offered, catalog(offered).split("\n"))}
                df = {w: sum(w in d for d in docs.values()) for d in docs.values() for w in set(d)}
                qset = set(toks(q))
                score = {h: sum(math.log(1 + len(docs) / df[w]) for w in set(d) if w in qset) for h, d in docs.items()}
                best = max(score, key=score.get) if score else None
                chosen = [best] if best and score[best] > 0 else []
            elif a.autoscope_mode == "pointwise":   # S5b: one yes/no judgement per helper
                o1 = chat(f"{q}\n\nFor EACH helper function below, decide whether a correct program for THIS task needs to call it. "
                          f"Answer one line per helper as `name: yes` or `name: no` (say yes only if it is directly needed).\n"
                          f"{catalog(offered)}", think=a.think, max_tokens=1024, temperature=a.temperature, seed=sd_)
                chosen = [m_.group(1) for m_ in re.finditer(r"(\w+)\s*:\s*yes\b", o1["text"] or "", re.I) if m_.group(1) in offered]
            else:
                o1 = chat(f"{q}\n\n" + (f"Your plan:\n{plan}\n\nNow decide which of these tested helper functions implement steps "
                          f"of YOUR plan" if plan else "Before writing any code, decide which of these tested helper functions you "
                          f"actually need for THIS task") + f" (often none or only one or two):\n{catalog(offered)}\n\nReply with only the "
                          f"names you will use, on the last line, as `HELPERS: name1, name2` (or `HELPERS: none`).", think=a.think,
                          max_tokens=1024, temperature=a.temperature, seed=sd_)
                line = ([l for l in (o1["text"] or "").splitlines() if "HELPERS" in l.upper()] or [""])[-1]
                chosen = [x for x in re.findall(r"\w+", line.split(":", 1)[-1]) if x in offered]
            tb = render_names(with_deps(chosen), a.tb_head)
            dis = [d for d in with_deps(chosen) if d not in GNEED[task]]
        hint_txt, hint_tok, hint_title = "", 0, None
        draft_code = None
        if a.self_hint:   # deployable (non-oracle) version of the text hint: the model names its own algorithm first, before seeing any helper
            oh = chat(f"{q}\n\nDo not write code yet. In one or two sentences, name the standard algorithm that solves this exactly and state "
                      f"its key formula or invariant.", think=False, max_tokens=200, temperature=a.temperature,
                      seed=None if a.seed is None else a.seed * 1000 + i + 100 * n + 13)
            hint_txt = "Your plan: " + strip_think(oh["text"] or "").strip()[:800]; hint_tok = oh.get("out_tokens") or 0
        elif a.hint_retrieve:   # realistic RAG for geometry: BM25 top-1 from the algorithm library (may be a near-miss)
            _, hint_title, htext = retrieve_hint(q)[0]
            hint_txt = f"Retrieved note ({hint_title}): {htext}"
        _gen = chat if a.think_budget < 0 else (lambda prompt, **kw: budget_chat(prompt, a.think_budget, **kw))
        prompt_txt = (f"{q}\n\n" + [f"Do not compute the answer by hand. Write a Python 3 program that solves this problem for any "
                 f"input in the following stdin format: {fmt}. Print only the answer. Give the program in a single "
                 f"```python code block.",
                 f"Solve this by writing code rather than by hand: give a complete Python 3 program (one ```python code block) that reads "
                 f"the input from stdin ({fmt}) and prints just the answer.",
                 f"Your task is to implement a Python 3 solution. Input arrives on standard input as follows: {fmt}. Output only the "
                 f"result. Put the whole program in a single ```python block; do not work the answer out manually."][a.prompt_variant] + (" Only the Python standard library is available (no third-party packages such as "
                 "shapely or numpy)." if a.stdlib else "") + (" Requirements: coordinates can be as large as 10^9 in absolute value, so "
                 "use exact integer arithmetic only (cross products; no floats, no division, no math.atan2/sqrt for "
                 "decisions), and handle degenerate cases correctly: duplicate points, collinear points, a query ray "
                 "passing exactly through a vertex, segments that only touch at an endpoint or overlap." if a.robust_hint else "")
                 + ("\n\n" + prims(task, a) if a.primitives else "")
                 + ("\n\n" + tb if tb else "")
                 + ("\nAPI contract: every point argument is ONE (x, y) tuple, e.g. orient((0, 0), (1, 0), (0, 1)) > 0, "
                    "segments_intersect((0, 0), (2, 2), (0, 2), (2, 0)) is True, on_segment((0, 0), (2, 2), (1, 1)) is True, "
                    "point_in_polygon([(0, 0), (4, 0), (0, 4)], (1, 1)) == 'inside'." if (a.tb_usage and tb) else "")
                 + (f"\n\nReminder: the program reads stdin in this format: {fmt}." if a.fmt_after else "")
                 + ("\n\n" + ALGO_HINT[task] if a.algo_hint and task in ALGO_HINT else "")
                 + ("\nMost of these helper functions are not needed for this task: use a helper only if your solution really needs it, "
                    "and do not let the available helpers change how you solve the task." if (a.scope_note and tb) else "")
                 + ("\n\n" + hint_txt if hint_txt else "")
                 + (f"\n\nExample stdin (this instance):\n```\n{render(task, V['identity'])[1]}```" if a.show_stdin else "")
                 + ("\n\nWrite the simplest brute-force program you can: correctness matters, speed does not (inputs are small)." if a.brute else ""))
        if a.s2a:   # B3: System 2 Attention (2311.11829), adapted to code: regenerate the context, then solve from it
            o_s2a = chat("Given the following programming task, extract the parts that are relevant for writing a correct program: the "
                         "problem, the input and output format, the instructions, and only those helper functions (copied unchanged) that a "
                         "correct solution actually needs. Leave out everything else. Output only the extracted text.\n\n---\n" + prompt_txt,
                         think=False, max_tokens=4096, temperature=a.temperature,
                         seed=None if a.seed is None else a.seed * 1000 + i + 100 * n + 29)
            hint_tok += o_s2a.get("out_tokens") or 0
            prompt_txt = strip_think(o_s2a["text"] or "").strip() or prompt_txt
        if (a.algo_first or a.algo_first_free) and tb:   # M4: algorithm first (no helpers), then refactor to use the offered helpers without changing the algorithm
            bare = prompt_txt.replace("\n\n" + tb, "", 1)
            sd_ = None if a.seed is None else a.seed * 1000 + i + 100 * n
            o1 = chat(bare, think=a.think, max_tokens=a.max_tokens, temperature=a.temperature, seed=sd_)
            from llm import chat_msgs
            o = chat_msgs([{"role": "user", "content": bare}, {"role": "assistant", "content": strip_think(o1["text"] or "")},
                           {"role": "user", "content": tb + "\nRewrite your program so that it uses these helpers wherever one of them does exactly what a "
                            "part of your program does." + ("" if a.algo_first_free else " Do not change your algorithm.") +
                            " Give the complete program in a single ```python code block."}],
                          think=a.think, max_tokens=a.max_tokens, temperature=a.temperature, seed=None if sd_ is None else sd_ + 7)
            hint_tok += o1.get("out_tokens") or 0
            draft_code = last_block(o1["text"] or "", ("python", "py", "python3"))
        else:
          o = _gen(prompt_txt,
                 think=a.think, max_tokens=a.max_tokens, temperature=a.temperature,
                 seed=None if a.seed is None else a.seed * 1000 + i + 100 * n, **({"logprobs": True} if a.logprobs else {}), **({"top_logprobs": a.logprobs_topk} if a.logprobs_topk else {}))
        code = last_block(o["text"], ("python", "py", "python3"))
        res = {}
        for vname, x in V.items():
            _, stdin, _ = render(task, x)
            if not code or (a.fast_fail and vname != "identity" and not res.get("identity")):   # H1: skip the other copies once the original fails
                res[vname] = None if vname == "identity" or not code else False; continue
            pre = ("\n".join(re.findall(r"```python\n(.*?)```", tb, re.S)) + "\n") if (a.tb_head == "prelude" and tb) else ""
            if a.tb_api and tb:   # L1: make `import geomlib` work inside the sandbox
                pre = ("import sys as _s, types as _t\n_m = _t.ModuleType('geomlib')\nexec(" + repr(api_src) + ", _m.__dict__)\n"
                       "_s.modules['geomlib'] = _m\n")
            r = run_python(pre + code, stdin, timeout=10)
            out = (r.stdout.strip().split() or [None])[-1] if r.status == "ok" else None
            res[vname] = None if out is None and vname == "identity" else (out is not None and out.lower() == answer(task, x))
        called = [d for d in dis if code and len(re.findall(rf"\b{d}\s*\(", code)) > (1 if f"def {d}(" in code else 0)]
        return {"task": task, "n": n, "inst": i, "per_variant": res, "class": classify(res), "code": code,
                "distractors": dis, "distractors_called": called, "autoscope_offered": offered, "autoscope_chosen": chosen,
                "out_tokens": (o.get("out_tokens") or 0) + hint_tok, "think_tokens": o.get("think_tokens"), "finish": o.get("finish"),
                "hint": hint_txt or None, "hint_title": hint_title, **({"prompt": prompt_txt} if a.save_prompt else {}),
                **({"draft_code": draft_code} if draft_code is not None else {}),
                **({"lp": o.get("lp"), "lp_tok": o.get("lp_tok")} if (a.logprobs or a.logprobs_topk) else {}),
                **({"ctop": o.get("ctop")} if a.logprobs_topk else {})}
    out_path = f"{RES}/geocross_{a.model_tag}.jsonl"
    prev = []
    if "--resume" in sys.argv and os.path.exists(out_path):   # keep finished rows after a server crash (2026-10-17)
        prev = [json.loads(l) for l in open(out_path, errors='replace') if l.strip() and not l.startswith(chr(0))]   # skip a NUL-filled torn line (2026-10-18)
        done = {(r["task"], r["n"], r["inst"]) for r in prev}
        jobs = [j for j in jobs if (j[0], j[1], j[2]) not in done]
    with ThreadPoolExecutor(64) as ex, open(out_path, "a" if prev else "w") as f:
        rows = list(prev)
        for r in ex.map(run, jobs):   # written as they complete (in order): a server crash keeps the finished rows (2026-10-17)
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    c = Counter(r["class"] for r in rows)
    print(a.model_tag, dict(c))
    for task in sizes:
        print(" ", task, dict(Counter(r["class"] for r in rows if r["task"] == task)))


if __name__ == "__main__":
    main()
