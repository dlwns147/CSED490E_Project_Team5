"""PREREG_DIFF addendum RELOOP-B (2026-11-25): ReLoop (Lian et al., NeurIPS 2026, arXiv 2602.15983; github.com/junbolian/ReLoop, MIT) as a recent-research baseline on our word problems, its official pipeline unchanged
(structured generation with data extraction -> L1 execution check + regeneration -> L2 perturbation tests CPT / OPT -> diagnosis-guided repair, 3 + 3 rounds; run_ablation.run_item is followed step by step), with gpt-oss-120b medium.
Ours is only the client: the served model, reasoning effort medium, 16,000 output tokens per call (theirs: 8,192, or 16,384 for reasoning models), their temperature 0 / seed 0. Every call's completion tokens are charged. Solver gurobipy (pip, size-limited licence,
as for OptiMind). Stages stored: cot (generation only), l1, final. An INFEASIBLE final program counts as "No Best Solution". Graded by run_nlopt.correct like every other arm.
usage: POC_BASE_URL=... POC_REASONING_EFFORT=medium python wp_reloop.py run <set> [...]  |  python wp_reloop.py score"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
REPO = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "baselines", "ReLoop")
R3 = f"{ROOT}/results/x3"
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


class Client:
    """their UsageLLM interface (generate(prompt, system, temperature)) on our server"""
    def __init__(self):
        import llm
        self.c, self.eff, self.tok, self.calls, self.cut, self.fail = llm.client, llm._EFF, 0, 0, 0, 0

    def generate(self, prompt, system=None, temperature=None):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        try:
            r = self.c.chat.completions.create(model="local", messages=msgs, temperature=0 if temperature is None else temperature, seed=0, max_tokens=16000, extra_body=self.eff)
        except Exception:
            self.fail += 1; raise
        self.calls += 1; self.tok += r.usage.completion_tokens; self.cut += r.choices[0].finish_reason == "length"
        return r.choices[0].message.content or ""


def run(sets):
    sys.path.insert(0, REPO)
    from reloop import CodeGenerator, ReLoopPipeline, CodeExecutor
    for st in sets:
        os.environ["NLOPT_SET"] = st
        import run_nlopt as RN
        P = RN.problems(st); out = f"{R3}/opt_reloop120_{st}_s1.jsonl"
        done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()

        def one(p):
            L = Client(); ex = CodeExecutor(); z = {"id": p["id"], "gold": p["gold"], "err": ""}
            g = lambda o: RN.correct(o, p["gold"]) if o is not None else False
            try:
                gen = CodeGenerator(llm_client=L, use_structured_generation=True); pipe = ReLoopPipeline(llm_client=L, enable_cpt=True, max_repair_iterations=3, verbose=False)
                data = {}; code = gen.generate(p["q"])
                if gen.extracted_data is not None:
                    data = gen.extracted_data
                e = ex.execute(code, data); cot = e.get("objective") if e.get("status") != "INFEASIBLE" else "NBS"; z.update(cot=cot, cot_ok=g(cot), cot_tok=L.tok, cot_status=e.get("status"), extracted=bool(data))
                r = pipe.run(problem_description=p["q"], data=data, initial_code=code)
                fin = r.final_report.objective; st_ = r.final_report.status
                if fin is None and ex.execute(r.final_code, data).get("status") == "INFEASIBLE":
                    fin = "NBS"
                z.update(l1=r.l1_checkpoint_obj, l1_ok=g(r.l1_checkpoint_obj), pred=fin, correct=g(fin), status=st_, regen=r.regeneration_count, iters=r.iterations)
            except Exception as x:
                z.update(err=repr(x)[:300]); z.setdefault("pred", None); z.setdefault("correct", False)
            z.update(out_tokens=L.tok, calls=L.calls, cut=L.cut, failed_requests=L.fail)
            return z
        with ThreadPoolExecutor(24) as tp, open(out, "a") as f:
            for z in tp.map(one, [p for p in P if p["id"] not in done]):
                f.write(json.dumps(z) + "\n"); f.flush()
        print(st, "done", flush=True)


def score():
    import wp_crossref as C
    ci = C.ci; tot = {"one": [], "RETRY": [], "ReLoop": []}
    for st in C.NINE + ("easyc", "nl4c", "omtf2"):
        f = f"{R3}/opt_reloop120_{st}_s1.jsonl"
        if not os.path.exists(f):
            continue
        RN, P, A, _, _, A2 = C.load(st); R = {json.loads(l)["id"]: json.loads(l) for l in open(f)}
        ids = [i for i in P if i in R]; n = len(ids)
        one = [(bool(A[i]["correct"]), C.tk(A[i])) for i in ids]
        ret = [one[k] if A[i]["pred"] is not None else (bool(A2[i]["correct"]), C.tk(A[i]) + C.tk(A2[i])) for k, i in enumerate(ids)]
        rl = [(bool(R[i]["correct"]), R[i]["out_tokens"]) for i in ids]
        for k, v in zip(tot, (one, ret, rl)):
            tot[k] += v
        s = lambda v: f"{100*sum(a for a, _ in v)/n:.1f}% @ {sum(t for _, t in v)/n/1000:.2f}k"
        print(f"{st:9s} n={n:3d} one {s(one)} | RETRY {s(ret)} | ReLoop {s(rl)} (generation only {100*sum(bool(R[i].get('cot_ok')) for i in ids)/n:.1f}%, after L1 {100*sum(bool(R[i].get('l1_ok')) for i in ids)/n:.1f}%); no value {sum(R[i]['pred'] is None for i in ids)}, "
              f"errors {sum(bool(R[i]['err']) for i in ids)}, failed requests {sum(R[i]['failed_requests'] > 0 for i in ids)}, zero-token {sum(R[i]['out_tokens'] == 0 for i in ids)}, cut calls {sum(R[i]['cut'] > 0 for i in ids)}"
              f" | ReLoop − RETRY acc {ci([100*(a[0]-b[0]) for a, b in zip(rl, ret)])}")
    n = len(tot["one"])
    for k, v in tot.items():
        print(f"pooled {k}: n={n} {100*sum(a for a, _ in v)/n:.1f}% @ {sum(t for _, t in v)/n/1000:.2f}k utility {sum(U(*x) for x in v)/n:.2f}")
    for x, y in (("ReLoop", "one"), ("ReLoop", "RETRY")):
        print(f"pooled {x} − {y}: accuracy {ci([100*(a[0]-b[0]) for a, b in zip(tot[x], tot[y])])} ktok {ci([(a[1]-b[1])/1000 for a, b in zip(tot[x], tot[y])])} utility {ci([U(*a)-U(*b) for a, b in zip(tot[x], tot[y])])}")


if __name__ == "__main__":
    run(sys.argv[2:]) if sys.argv[1] == "run" else score()
