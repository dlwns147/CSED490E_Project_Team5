"""MT (docs/prereg/PREREG_MT.md): multi-turn function calling (BFCL v4 multi_turn_base / miss_param / miss_func, prompt mode), where
the free check is what the environment shows at every step (an error, or no progress). One arm per run (each arm is its own trajectory: a step changes the state the next step
sees). Per item: BFCL's system prompt with the involved classes' function docs, then each turn's user message; within a turn the model
answers, its calls ([func(arg=value), ...], decoded as BFCL's default_decode_execute_prompting) run in BFCL's own environment
classes (multi_turn_utils.execute_multi_turn_func_call), each result goes back as a tool message, until the model answers without a
decodable call (the turn ends) or after 20 steps (BFCL's limit: the item fails; so does a conversation that outgrows the context). Arms, per step:
  N  non-thinking (2,048-token cap)
  T  thinking (8,192-token cap)
  E  the free check at every step: non-thinking, but thinking for the step after a visible failure of the previous step (same turn):
     a call returned an error (an "Error during execution" string or a JSON object with an "error" key), or the step repeated the
     previous step's calls with the same results (no progress; added after the smoke, where non-thinking loops ended 4 of 10 items);
     the failed step and its results stay in the context
  F  thinking for the first step of each turn (the new request), then as E
Rows (results/tc/mt_<tag>_<arm>_s<seed>.jsonl): per turn, per step {calls, think, tok, err, end}; the item's output tokens; graded
offline by poc/grade_mt.py (BFCL's multi_turn_checker). Rows resume.
  V  (MT-V, PREREG_MT addendum MT-V) per turn, sandboxed rollouts of the quick turn, the peer's quick turn (another model's server,
     POC_PEER_URL) and two thinking turns, made and committed by the per-turn policy learned on the other half's turn 0 (MT_POLICY)
  U  (addendum MT-SO-ENV) S with the item's environment group (analyze_mtb.env_half) in place of its scenario half: the verifier
     mtsoenv_h<1-g>, the fit results/tc/mt_soenv_fit_<tag>.json; only the items whose classes are all in one group
  S  (MT-SO, addendum MT-SO) per turn, sandboxed rollouts N, P, T; a trained verifier (LoRA on the MT_VER server: gen or peer) scores
     them and the set-choice fit fitted on the other half (results/tc/mt_so_fit_<tag>.json) commits one
usage: python run_mt.py <tag> <arm N|T|E|F|V|S|U> <seed>     (MT_SUBSET=i/k: items i, i+k, ... only — the smoke; MT_WORKERS, default 8)"""
import ast, copy, json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.dont_write_bytecode = True   # the BFCL package is imported read-only from the grader venv (through $POC_DATA/bfcl/pkg)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_msgs  # noqa: E402
from openai import BadRequestError  # noqa: E402
from run_nlopt import _rows  # noqa: E402

PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
sys.path.insert(0, os.path.join(PD, "bfcl", "pkg"))
import bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils as U  # noqa: E402

# SIDE-ENV (PREREG_SIDE.md): generated environments outside BFCL, MT_CLASSES="Class=module,..." (modules under the repo, e.g.
# PackageManagerAPI=side.envs.package_manager), with MT_ITEMS naming their items
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _x in filter(None, os.environ.get("MT_CLASSES", "").split(",")):
    U.CLASS_FILE_PATH_MAPPING[_x.split("=")[0]] = _x.split("=")[1]

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
DATA = os.environ.get("MT_ITEMS") or os.path.join(PD, "bfcl", "mt_items.jsonl")
NMAX, TMAX, STEPS = 2048, 8192, 20


# BFCL's prompt-mode decoder (bfcl_eval.model_handler.utils: default_decode_execute_prompting, ast_parse for Python,
# resolve_ast_call, resolve_ast_by_type, parse_nested_value, decoded_output_to_execution_list), copied because that module imports
# parsers the client venv lacks
def _call(elem):
    parts, f = [], elem.func
    while isinstance(f, ast.Attribute):
        parts.append(f.attr); f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return {".".join(reversed(parts)): {a.arg: _val(a.value) for a in elem.keywords}}


def _val(v):
    if isinstance(v, ast.Constant):
        return "..." if v.value is Ellipsis else v.value
    if isinstance(v, ast.UnaryOp):
        return -v.operand.value
    if isinstance(v, ast.List):
        return [_val(x) for x in v.elts]
    if isinstance(v, ast.Dict):
        return {_val(k): _val(x) for k, x in zip(v.keys, v.values)}
    if isinstance(v, ast.BinOp):
        return eval(ast.unparse(v))
    if isinstance(v, ast.Name):
        return v.id
    if isinstance(v, ast.Call):
        return ast.unparse(v) if not v.keywords else _call(v)
    if isinstance(v, ast.Tuple):
        return tuple(_val(x) for x in v.elts)
    if isinstance(v, ast.Lambda):
        return eval(ast.unparse(v.body[0].value))
    if isinstance(v, ast.Subscript):
        try:
            return ast.unparse(v.body[0].value)
        except Exception:
            return ast.unparse(v.value) + "[" + ast.unparse(v.slice) + "]"
    raise Exception(f"Unsupported AST type: {type(v)}")


def _nested(v):
    if isinstance(v, dict):
        if all(isinstance(x, dict) for x in v.values()):
            f = list(v)[0]
            return f"{f}({', '.join(f'{k}={_nested(x)}' for k, x in v[f].items())})"
        return "{" + ", ".join(f"'{k}': {_nested(x)}" for k, x in v.items()) + "}"
    return repr(v)


def decode(text):
    s = text.strip("`\n ")
    if not s.startswith("["):
        s = "[" + s
    if not s.endswith("]"):
        s = s + "]"
    p = ast.parse(s.strip().strip("'"), mode="eval")
    calls = [_call(p.body)] if isinstance(p.body, ast.Call) else []
    if not calls:
        for e in p.body.elts:
            assert isinstance(e, ast.Call)
            calls.append(_call(e))
    return [f"{k}({', '.join(f'{a}={_nested(x)}' for a, x in v.items())})" for c in calls for k, v in c.items()]


def is_err(res):
    if res.startswith("Error during execution"):
        return True
    try:
        d = json.loads(res)
    except Exception:
        return False
    return isinstance(d, dict) and "error" in d


def answer(msgs, think, seed, model="local"):
    try:
        o = chat_msgs(msgs, model=model, think=think, max_tokens=TMAX if think else NMAX, temperature=0.7, seed=seed)
    except BadRequestError as e:   # the conversation outgrew the context: the item fails, as an inference error fails it in BFCL
        if "context" not in str(e).lower() and "too long" not in str(e).lower() and "maximum" not in str(e).lower():
            raise
        return "", 0, "overflow"
    t = o["text"]
    if "</think>" in t:
        t = t.split("</think>")[-1]
    if "<think>" in t:   # the think never closed (cap reached): no answer
        t = ""
    return t.strip(), o["out_tokens"], o["finish"]


def _inst(name, pid, c):
    return re.sub(r"[-./:]", "_", f"{name}_{pid}_{c}_instance")


def run_turn(p, msgs, name, ti, think, seed, cli, lc):
    """MT-V: one turn from msgs on the instances under `name` (a sandbox copy); -> (new messages, steps, out tokens, quit, visible)"""
    cfg, cls = p["initial_config"], p["involved_classes"]
    msgs = list(msgs); start = len(msgs)
    steps, tok, quit_, vis = [], 0, False, False
    for k in range(STEPS + 1):
        sd = seed * 100003 + zlib.crc32(f"{p['id']}/{ti}/{k}".encode()) % 99991
        try:
            o = chat_msgs(msgs, think=think, max_tokens=TMAX if think else NMAX, temperature=0.7, seed=sd, client_=cli)
            text, n, fin = o["text"], o["out_tokens"], o["finish"]
            if "</think>" in text:
                text = text.split("</think>")[-1]
            if "<think>" in text:
                text = ""
            text = text.strip()
        except BadRequestError as e:
            if "context" not in str(e).lower() and "too long" not in str(e).lower() and "maximum" not in str(e).lower():
                raise
            steps.append({"calls": [], "think": think, "tok": 0, "fin": "overflow"}); return msgs[start:], steps, tok, True, True
        tok += n
        msgs.append({"role": "assistant", "content": text})
        try:
            calls = decode(text)
        except Exception:
            calls = []
        if not calls:
            steps.append({"calls": [], "think": think, "tok": n, "fin": fin, "text": text[:300]})
            break
        res, _ = U.execute_multi_turn_func_call(calls, cfg, cls, name, p["id"], long_context=lc)
        errs = [is_err(r) for r in res]
        for c, r in zip(calls, res):
            msgs.append({"role": "tool", "name": c, "content": r})
        loop = bool(steps) and steps[-1]["calls"] == calls and steps[-1].get("full") == res
        steps.append({"calls": calls, "think": think, "tok": n, "fin": fin, "err": errs, "loop": loop, "res": [r[:200] for r in res], "full": res})
        vis = vis or any(errs) or loop
        if k == STEPS:
            quit_ = True; vis = True
    for st in steps:
        st.pop("full", None)
    return msgs[start:], steps, tok, quit_, vis


def run_item_vote(p, tag, seed):
    """MT-V: per turn, rollouts of the quick turn (N), the peer's quick turn (P), the thinking turn (T) and a second thinking turn (T at
    the next seed) on sandbox copies of the committed environment, made and committed as the turn-0 policy learned on the other half
    of the items says (mt_policy.py); the committed turn's steps are the row's turn (graded as any arm's)."""
    import copy
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import _compare_instances
    pol = _policy(p["id"])
    name = f"{tag}_V_s{seed}"
    cfg, cls, lc = p["initial_config"], p["involved_classes"], "long_context" in p["cat"]
    U.execute_multi_turn_func_call([], cfg, cls, name, p["id"], long_context=lc)
    msgs = [{"role": "system", "content": p["system"]}]
    turns, votes, tok, quit_ = [], [], 0, False
    spec = [(False, seed, None), (False, seed, PEER), (True, seed, None), (True, seed % 3 + 1, None)]   # N, P, T, T2
    for ti, um in enumerate(p["turns"]):
        msgs += um
        cand, obs, reps, made, fallback = {}, [None] * 4, [], [], False
        while True:
            key = repr(tuple(_canon(obs)))
            act = pol.get(key)
            if act is None:   # a pattern the fitting half never showed: the always-think baseline (T, else commit T's state)
                fallback = True
                act = ["call", 2] if obs[2] is None else ["stop", _canon(obs)[2][0]]
            if act[0] == "stop":
                g = act[1]
                cobs = _canon(obs)
                j = next(j for j in range(4) if cobs[j] is not None and cobs[j][0] == g)
                break
            j = act[1]; think, sd, cli = spec[j]
            cname = f"{name}_t{ti}_c{j}"
            for c in cls:   # sandbox: a deep copy of the committed instances
                U.__dict__[_inst(cname, p["id"], c)] = copy.deepcopy(U.__dict__[_inst(name, p["id"], c)])
            new, steps, n, q, vis = run_turn(p, msgs, cname, ti, think, sd, cli, lc)
            tok += n; made.append(j)
            state = {c: U.__dict__[_inst(cname, p["id"], c)] for c in cls}
            g = next((gi for gi, r in enumerate(reps) if all(_compare_instances(state[c], r[c])[0] for c in cls)), None)
            if g is None:
                reps.append(state); g = len(reps) - 1
            cand[j] = (new, steps, q, state)
            obs[j] = (g, not vis)
        new, steps, q, state = cand[j]
        for c in cls:   # commit the chosen rollout's environment
            U.__dict__[_inst(name, p["id"], c)] = state[c]
        for jj in cand:
            for c in cls:
                U.__dict__.pop(_inst(f"{name}_t{ti}_c{jj}", p["id"], c), None)
        msgs += new
        turns.append(steps)
        votes.append({"calls": made, "commit": j, "pattern": repr(tuple(_canon(obs))), "fallback": fallback})
        if q:
            quit_ = True
            break
    for c in cls:
        U.__dict__.pop(_inst(name, p["id"], c), None)
    return {"id": p["id"], "cat": p["cat"], "arm": "V", "seed": seed, "turns": turns, "tok": tok, "force_quit": quit_, "votes": votes,
            "n_think": sum(s["think"] for t in turns for s in t), "n_steps": sum(len(t) for t in turns)}


def run_item_sel(p, tag, seed, arm="S"):
    """MT-SO (PREREG_MT addendum MT-SO): per turn, rollouts of the quick turn (N), the peer's quick turn (P) and the thinking turn (T) on
    sandbox copies of the committed environment; the verifier trained on the other half of the scenarios (LoRA mtso_h<1-h> on the
    MT_VER server, gen or peer) scores each distinct rollout as mt_peer0.render shows it after mt_peer0.turn_context, and the set-choice
    fit of the item's half (results/tc/mt_so_fit_<tag>.json, analyze_mtb.py --sel2) chooses; a structure the fit never saw commits T.
    The chosen rollout's steps and environment continue the conversation; every rollout's output tokens count.
    arm U (addendum MT-SO-ENV): the item's environment group in place of its half, verifier mtsoenv_h<1-g>, fit mt_soenv_fit_<tag>.json."""
    import copy, math
    from mt_peer0 import render, short_system, turn_context
    from tc_train import TC_ASK
    if arm == "U":
        h = _envh()[p["id"]]
        fit, ver = _sofit(tag, "soenv")[f"h{h}"], f"mtsoenv_h{1 - h}"
    else:
        h = zlib.crc32(p["id"].rsplit("_", 1)[1].encode()) % 2
        fit, ver = _sofit(tag)[f"h{h}"], f"mtso_h{1 - h}"
    vcli = PEER if os.environ.get("MT_VER", "gen") == "peer" else None
    from llm import client as gcli
    name = f"{tag}_{arm}_s{seed}"
    cfg, cls, lc = p["initial_config"], p["involved_classes"], "long_context" in p["cat"]
    U.execute_multi_turn_func_call([], cfg, cls, name, p["id"], long_context=lc)
    msgs = [{"role": "system", "content": p["system"]}]
    turns, choices, tok, vpre, quit_ = [], [], 0, 0, False
    spec = {"N": (False, None), "P": (False, PEER), "T": (True, None)}
    for ti, um in enumerate(p["turns"]):
        msgs += um
        cand = {}
        for j, (think, cli) in spec.items():
            cname = f"{name}_t{ti}_{j}"
            for c in cls:   # sandbox: a deep copy of the committed instances
                U.__dict__[_inst(cname, p["id"], c)] = copy.deepcopy(U.__dict__[_inst(name, p["id"], c)])
            new, steps, n, q, vis = run_turn(p, msgs, cname, ti, think, seed, cli, lc)
            tok += n
            cand[j] = (new, steps, q, {c: U.__dict__[_inst(cname, p["id"], c)] for c in cls}, render(steps), n)
        groups = {}
        for j in spec:
            groups.setdefault(cand[j][4], []).append(j)
        names = {re.sub(r"\(.*", "", c) for j in spec for z in cand[j][1] for c in z["calls"]}
        sysm = short_system(p, names)
        C = []
        for txt, js in groups.items():
            m = [{"role": "system", "content": sysm}, {"role": "user", "content": turn_context(p, ti)},
                 {"role": "assistant", "content": txt}, {"role": "user", "content": TC_ASK}]
            o = (vcli or gcli).chat.completions.create(model=ver, messages=m, max_tokens=1, temperature=0, logprobs=True, top_logprobs=20,
                                                         extra_body={"chat_template_kwargs": {"enable_thinking": False}})
            top = {t.token: t.logprob for t in o.choices[0].logprobs.content[0].top_logprobs}
            lo = min(top.values())
            vpre += o.usage.prompt_tokens
            C.append({"calls": tuple(sorted(js)), "s": top.get("ACCEPT", lo) - top.get("DE", lo)})
        S = repr(tuple(sorted(c["calls"] for c in C)))
        key = lambda c: f"{S}|{c['calls']!r}"
        if any(key(c) not in fit["cnt"] for c in C):
            ch, unseen = "T", True
        else:
            mu = sum(c["s"] for c in C) / len(C)
            lg = lambda c: math.log((fit["rt"][key(c)] + 0.5) / (fit["cnt"][key(c)] + 1))
            ch, unseen = max(C, key=lambda c: lg(c) + fit["beta"] * (c["s"] - mu) / fit["sd"])["calls"][0], False
        new, steps, q, state, _, _ = cand[ch]
        for c in cls:   # commit the chosen rollout's environment
            U.__dict__[_inst(name, p["id"], c)] = state[c]
        for j in spec:
            for c in cls:
                U.__dict__.pop(_inst(f"{name}_t{ti}_{j}", p["id"], c), None)
        msgs += new
        turns.append(steps)
        choices.append({"commit": ch, "unseen": unseen, "sets": [[list(c["calls"]), round(c["s"], 4)] for c in C],
                        "tok": {j: cand[j][5] for j in spec}})
        if q:
            quit_ = True
            break
    for c in cls:
        U.__dict__.pop(_inst(name, p["id"], c), None)
    return {"id": p["id"], "cat": p["cat"], "arm": arm, "seed": seed, "turns": turns, "tok": tok, "force_quit": quit_, "choices": choices,
            "ver_prefill": vpre, "n_think": sum(s["think"] for t in turns for s in t), "n_steps": sum(len(t) for t in turns)}


_SOFIT, _ENVH = {}, {}


def _sofit(tag, kind="so"):
    """MT-SO: the set-choice fit per item half (fitted on the other half), keys '<structure>|<roles>' as analyze_mtb.py --sel2 writes;
    kind soenv (MT-SO-ENV): per environment group, MT_SEL_SPLIT=env analyze_mtb.py --sel2"""
    if (tag, kind) not in _SOFIT:
        f = f"{RES}/mt_{kind}_fit_{tag}.json"
        _SOFIT[(tag, kind)] = json.load(open(os.environ.get("MT_SO_FIT", f) if kind == "so" else f))
    return _SOFIT[(tag, kind)]


def _envh():
    """MT-SO-ENV: item -> environment group (0 / 1, None for items of both), as MT-SEL-ENV split BFCL's classes"""
    if not _ENVH:
        from analyze_mtb import env_half
        _ENVH.update(env_half(DATA))
    return _ENVH


def _canon(obs):
    """lcm_bound.project's canonical form: groups relabelled by first appearance in call order"""
    m, out = {}, []
    for e in obs:
        if e is None or e[0] == "X":
            out.append(e)
        else:
            m.setdefault(e[0], len(m)); out.append((m[e[0]], e[1]))
    return out


PEER, _POL = None, {}


def _policy(pid):
    """the policy fitted on the other half of the items (crc32(id) mod 2)"""
    h = 1 - zlib.crc32(pid.encode()) % 2
    if h not in _POL:
        f = os.environ["MT_POLICY"].replace("{h}", str(h))
        _POL[h] = json.load(open(f))["policy"]
    return _POL[h]


def run_item(p, tag, arm, seed):
    name = f"{tag}_{arm}_s{seed}"
    # addendum MT-RF: MT_N_LORA=<prefix>: quick steps come from the adapter <prefix><h> trained on the other half of the scenarios
    nmodel = (os.environ["MT_N_LORA"] + str(1 - zlib.crc32(p["id"].rsplit("_", 1)[1].encode()) % 2)) if os.environ.get("MT_N_LORA") else "local"
    cfg, cls, lc = p["initial_config"], p["involved_classes"], "long_context" in p["cat"]
    U.execute_multi_turn_func_call([], cfg, cls, name, p["id"], long_context=lc)   # fresh instances for this trajectory
    msgs = [{"role": "system", "content": p["system"]}]
    turns, tok, quit_ = [], 0, False
    for ti, um in enumerate(p["turns"]):
        msgs += um
        steps, prev_err = [], False   # a visible failure flags the next step of the same request only
        for k in range(STEPS + 1):
            think = arm == "T" or (arm in ("E", "F") and prev_err) or (arm == "F" and k == 0)
            sd = seed * 100003 + zlib.crc32(f"{p['id']}/{ti}/{k}".encode()) % 99991
            text, n, fin = answer(msgs, think, sd, nmodel if not think else "local")
            tok += n
            if fin == "overflow":
                steps.append({"calls": [], "think": think, "tok": 0, "fin": fin})
                quit_ = True
                break
            msgs.append({"role": "assistant", "content": text})
            try:
                calls = decode(text)
            except Exception:
                calls = []
            if not calls:
                steps.append({"calls": [], "think": think, "tok": n, "fin": fin, "text": text[:300]})
                break
            res, _ = U.execute_multi_turn_func_call(calls, cfg, cls, name, p["id"], long_context=lc)
            errs = [is_err(r) for r in res]
            for c, r in zip(calls, res):
                msgs.append({"role": "tool", "name": c, "content": r})
            loop = bool(steps) and steps[-1]["calls"] == calls and steps[-1].get("full") == res
            steps.append({"calls": calls, "think": think, "tok": n, "fin": fin, "err": errs, "loop": loop, "res": [r[:200] for r in res],
                          "full": res})
            prev_err = any(errs) or loop
            if k == STEPS:
                quit_ = True
        for st in steps:
            st.pop("full", None)
        turns.append(steps)
        if quit_:
            break
    for c in cls:   # free the trajectory's instances
        U.__dict__.pop(re.sub(r"[-./:]", "_", f"{name}_{p['id']}_{c}_instance"), None)
    return {"id": p["id"], "cat": p["cat"], "arm": arm, "seed": seed, "turns": turns, "tok": tok, "force_quit": quit_,
            "n_think": sum(s["think"] for t in turns for s in t), "n_steps": sum(len(t) for t in turns)}


def main():
    tag, arm, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    assert arm in ("N", "T", "E", "F", "V", "S", "U")
    if arm in ("V", "S", "U"):   # MT-V: the peer's server (POC_PEER_URL) and the policy files (MT_POLICY, with {h} for the fitting half); MT-SO: MT_VER
        global PEER
        from openai import OpenAI
        PEER = OpenAI(base_url=os.environ["POC_PEER_URL"], api_key="none", timeout=float(os.environ.get("POC_TIMEOUT", 3600)))
    P = [json.loads(l) for l in open(DATA)]
    if os.environ.get("MT_SUBSET"):
        i, k = map(int, os.environ["MT_SUBSET"].split("/")); P = P[i::k]
    if arm == "U":   # MT-SO-ENV: the items of one environment group only
        P = [p for p in P if _envh().get(p["id"]) is not None]
    os.makedirs(RES, exist_ok=True)
    path = f"{RES}/mt_{tag}_{arm}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    todo = [p for p in P if p["id"] not in done]
    print(f"MT {tag} {arm} s{seed}: {len(todo)} of {len(P)} items to run", flush=True)
    with ThreadPoolExecutor(int(os.environ.get("MT_WORKERS", 8))) as ex, open(path, "a") as f:
        run = {"V": run_item_vote, "S": run_item_sel, "U": lambda p, tag, seed: run_item_sel(p, tag, seed, "U")}
        fs = {(ex.submit(run[arm], p, tag, seed) if arm in run else ex.submit(run_item, p, tag, arm, seed)): p["id"] for p in todo}
        for j, fu in enumerate(as_completed(fs)):
            try:
                r = fu.result()
            except Exception as e:
                print(f"  {fs[fu]}: {type(e).__name__}: {e}", flush=True)
                continue
            f.write(json.dumps(r) + "\n"); f.flush()
            if j % 20 == 0:
                print(f"  {j + 1}/{len(todo)} {r['id']} steps {r['n_steps']} think {r['n_think']} tok {r['tok']}", flush=True)


if __name__ == "__main__":
    main()
