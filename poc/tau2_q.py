"""tau2 rollouts per turn (PREREG_TAU): what each candidate turn is worth when no per-turn label exists. tau2 scores only the end of a
conversation, against a simulated user. So from a user message (a state of the conversation), each candidate agent turn is run in a
sandbox and the conversation continued to its end by the base policy; the end reward of that continuation is a Monte Carlo sample of
Q(state, candidate). Each conversation is then played by the rollout algorithm: commit the candidate turn whose rollout scored best (the
base policy's on a tie, which is no evidence), take the user's reply, repeat. Its final reward is a real sample of that policy's value.
The simulated user and the score are used, so this is an upper bound and the training labels, never a test-time method. Runs with the
tau2 venv's python, through lane.sh with POC_BASE_URL set (PEER_BASE_URL gives arm P, the peer model's quick turn):
  python poc/tau2_q.py <out tag> --domain retail --base runs/pilot_retail_T_s1.json --arms T,N --base-arm T --r 2 --workers 12 [--tasks N] [--user-args JSON] [--dry]
Writes $TAU2/runs/q_<tag>.jsonl: per rollout domain, task, t (which user message), plen, arm, r, committed, reward, term, cand (the candidate
turn's messages), ktok_cand, ktok_rest, sec, or err; per conversation a row with kind "final": reward, base_reward, turns, ktok, messages.
A conversation's rows are written when it ends, and finished conversations are skipped on a rerun."""
import argparse, hashlib, json, os, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TAU2 = Path(os.environ.get("TAU2_ROOT", "/home1/leesangjun/SJ/POSTECH/nlp_data/tau2"))
os.environ.setdefault("TAU2_DATA_DIR", str(TAU2 / "repo" / "data"))
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("OPENAI_API_KEY", "x")
if os.environ.get("POC_BASE_URL"):
    os.environ["OPENAI_API_BASE"] = os.environ["POC_BASE_URL"]

from loguru import logger

from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.data_model.semantic_communication import CommunicateScoring
from tau2.data_model.simulation import Results, TextRunConfig
from tau2.data_model.tasks import InitialState
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.runner.build import build_text_orchestrator
from tau2.runner.helpers import get_tasks
from tau2.user.user_simulator import UserSimulator

logger.remove()

ON = {"chat_template_kwargs": {"enable_thinking": True}}
OFF = {"chat_template_kwargs": {"enable_thinking": False}}
# the same settings as pilot.sh; P is the same quick turn from the peer model's server when one is given (PEER_BASE_URL)
ARGS = {
    "T": {"temperature": 0.7, "max_tokens": 6000, "extra_body": ON},
    "N": {"temperature": 0.7, "max_tokens": 2000, "extra_body": OFF},
}
if os.environ.get("PEER_BASE_URL"):
    ARGS["P"] = dict(ARGS["N"], api_base=os.environ["PEER_BASE_URL"])
USER = {"temperature": 0.0, "max_tokens": 800, "extra_body": OFF}
MAX_STEPS = 60


def states(sim):
    """every state a turn starts from: the prefixes ending in a user message that does not end the conversation"""
    out = []
    for i, m in enumerate(sim.messages):
        if isinstance(m, UserMessage) and not m.is_tool_call() and not UserSimulator.is_stop(m):
            out.append(i + 1)
    return out


def switch(agent, first, rest):
    """the candidate's settings until its first message to the user (the end of its turn), the base policy's after it"""
    gen, left = agent.generate_next_message, [True]
    agent.llm_args = dict(first)

    def g(msg, st):
        out, st = gen(msg, st)
        if left[0] and not out.is_tool_call():
            seed = agent.llm_args.get("seed")
            agent.llm_args = dict(rest, seed=seed) if seed is not None else dict(rest)
            left[0] = False
        return out, st

    agent.generate_next_message = g


def seed_of(*key):
    return int(hashlib.sha256(json.dumps(key).encode()).hexdigest()[:7], 16)


def build(cfg, task, prefix, arm, base_arm, seed):
    branch = task.model_copy(deep=True)
    old = task.initial_state
    branch.initial_state = InitialState(
        initialization_data=old.initialization_data if old else None,
        initialization_actions=old.initialization_actions if old else None,
        message_history=list(old.message_history or []) + prefix if old else prefix,
    )
    o = build_text_orchestrator(cfg, branch, seed=seed)
    switch(o.agent, ARGS[arm], ARGS[base_arm])
    o.max_steps = max(1, MAX_STEPS - len(prefix))  # the budget the whole conversation would have had
    return o


def ktok(ms):
    return sum(((m.usage or {}).get("completion_tokens") or 0) for m in ms if isinstance(m, AssistantMessage)) / 1000


def rollout(cfg, task, prefix, arm, base_arm, seed):
    """-> reward, how it ended, the candidate turn's messages, its tokens and the continuation's"""
    o = build(cfg, task, prefix, arm, base_arm, seed)
    sim = o.run()
    new = sim.messages[len(prefix):]
    # the base task, not the branch: the trajectory already holds the prefix, and the gold state starts from the task's own start
    info = evaluate_simulation(simulation=sim, task=task, evaluation_type=EvaluationType.ALL, solo_mode=False, domain=cfg.domain,
                               communicate_scoring=CommunicateScoring())
    end = next((i + 1 for i, m in enumerate(new) if isinstance(m, AssistantMessage) and not m.is_tool_call()), len(new))
    return float(info.reward), str(sim.termination_reason), new, end, info


def next_state(new, end):
    """from a rollout's messages and the end of its candidate turn: the messages up to the user's next message to the agent, or None if
    the conversation ends first"""
    for i in range(end, len(new)):
        if isinstance(new[i], UserMessage) and not new[i].is_tool_call():
            return None if UserSimulator.is_stop(new[i]) else new[: i + 1]
    return None


def play(cfg, task, sim, arms, base_arm, r_each, inner):
    """the rollout algorithm on one conversation, from the recorded conversation's first user message"""
    prefix, t, rows = list(sim.messages[: states(sim)[0]]), 0, []
    cands = [(arm, r) for arm in arms for r in range(r_each)]  # the base policy first: max() below keeps the first on a tie
    while True:
        def one(c):
            t0 = time.time()
            try:
                return c, rollout(cfg, task, prefix, c[0], base_arm, seed_of(task.id, t, c[0], c[1])), time.time() - t0, None
            except Exception as e:
                return c, None, time.time() - t0, repr(e)[:400]

        got = list(inner.map(one, cands))
        ok = [g for g in got if g[1] is not None]
        best = max(ok, key=lambda g: g[1][0]) if ok else None
        for c, out, sec, err in got:
            row = dict(domain=cfg.domain, task=task.id, t=t, plen=len(prefix), arm=c[0], r=c[1], sec=round(sec, 1), committed=bool(best and c == best[0]))
            if err:
                row.update(err=err)
            else:
                reward, term, new, end, info = out
                row.update(reward=reward, term=term, cand=[m.model_dump(mode="json", exclude={"raw_data"}) for m in new[:end]], ktok_cand=ktok(new[:end]), ktok_rest=ktok(new[end:]),
                           breakdown={str(k): v for k, v in (info.reward_breakdown or {}).items()})
            rows.append(row)
        if best is None:
            return rows + [dict(kind="final", domain=cfg.domain, task=task.id, err="every rollout failed", turns=t)]
        reward, term, new, end, info = best[1]
        step = next_state(new, end)
        if step is None:  # the committed rollout itself ended the conversation before another turn: its reward is the conversation's
            msgs = prefix + new
            return rows + [dict(kind="final", domain=cfg.domain, task=task.id, reward=reward, term=term, turns=t + 1, base_reward=sim.reward_info.reward if sim.reward_info else None, ktok=ktok(msgs),
                                messages=[m.model_dump(mode="json", exclude={"raw_data"}) for m in msgs])]
        prefix = prefix + step
        t += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--domain", required=True)
    ap.add_argument("--base", required=True, help="a tau2 results.json, the recorded conversations; relative to $TAU2")
    ap.add_argument("--arms", default="T,N")
    ap.add_argument("--base-arm", default="T")
    ap.add_argument("--r", type=int, default=2)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--user-args", default=None, help="JSON, replaces the simulated user's settings")
    ap.add_argument("--tasks", type=int, default=None)
    ap.add_argument("--split", default="train")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    res = Results.load(TAU2 / a.base)
    tasks = {t.id: t for t in get_tasks(a.domain, task_split_name=a.split)}
    cfg = TextRunConfig(domain=a.domain, task_split_name=a.split, llm_agent="openai/local", llm_args_agent=ARGS[a.base_arm], llm_user="openai/local",
                        llm_args_user=json.loads(a.user_args) if a.user_args else USER, max_steps=MAX_STEPS, max_errors=10, seed=0)
    path = TAU2 / "runs" / f"q_{a.tag}.jsonl"
    done = set()
    if path.exists():
        for line in open(path):
            try:
                q = json.loads(line)
            except json.JSONDecodeError:
                continue
            if q.get("kind") == "final" and "err" not in q:
                done.add(q["task"])
    sims = res.simulations[:a.tasks] if a.tasks else res.simulations
    sims = [s for s in sims if s.task_id not in done and states(s)]
    arms = a.arms.split(",")
    print(f"tau2_q {a.tag}: {len(sims)} conversations left", flush=True)
    if a.dry:
        s = sims[0]
        o = build(cfg, tasks[s.task_id], s.messages[:states(s)[0]], arms[-1], a.base_arm, 1)
        o.initialize()
        print("branch built; from", o.from_role, "to", o.to_role, "; history", len(o.trajectory), "; max_steps", o.max_steps, flush=True)
        return
    lock = threading.Lock()
    f = open(path, "a")
    width = len(arms) * a.r
    inner = ThreadPoolExecutor(a.workers)  # one pool of rollouts; each conversation waits for its own

    def conv(s):
        rows = play(cfg, tasks[s.task_id], s, arms, a.base_arm, a.r, inner)
        with lock:
            for row in rows:
                f.write(json.dumps(row) + "\n")
            f.flush()
        last = rows[-1]
        print(a.tag, s.task_id, "turns", last.get("turns"), "reward", last.get("reward"), "base", last.get("base_reward"), flush=True)

    with ThreadPoolExecutor(max(1, a.workers // width)) as ex:
        list(ex.map(conv, sims))
    f.close()
    os.chmod(path, 0o644)
    print(f"tau2_q {a.tag}: done", flush=True)


if __name__ == "__main__":
    main()
