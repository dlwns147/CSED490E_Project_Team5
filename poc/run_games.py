"""PoC A — interactive algorithmic strategy: does an LLM search information-optimally in a dialogue?

guess    : secret integer in [1, N]; each GUESS x is answered CORRECT / HIGHER / LOWER.
           Optimal worst case = ceil(log2(N+1)) guesses (binary search).
mastermind: 4 pegs, 6 colours A-F, repeats allowed; feedback = (black, white).
           Knuth's minimax strategy needs <= 5 guesses; a "play any consistent code" strategy averages ~5.
Per guess we also record whether it was CONSISTENT with all feedback so far (a wasted query otherwise),
and for `guess` how close it was to the midpoint of the feasible interval.
"""
import argparse
import itertools
import json
import math
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, strip_think  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"

GUESS_RULES = ("Let's play a game. I have chosen a secret integer between 1 and {N} (inclusive). Find it using as "
               "few guesses as possible. Each turn, reply with one guess on the last line in the form `GUESS x`. "
               "I will answer CORRECT, HIGHER (the secret is larger than x) or LOWER (the secret is smaller than x). "
               "Use the best possible strategy. Reply with ONLY your guess on a single line, e.g. `GUESS 50`, with no "
               "explanation.")
MM_RULES = ("Let's play Mastermind. I have chosen a secret code of 4 pegs; each peg is one of the colours "
            "A, B, C, D, E, F, and colours may repeat. Each turn, reply with one guess on the last line in the form "
            "`GUESS ABCD`. I will answer with the number of BLACK pegs (right colour, right position) and WHITE pegs "
            "(right colour, wrong position). Find the code in as few guesses as possible using the best strategy. "
            "Reply with ONLY your guess on a single line, e.g. `GUESS AABB`, with no explanation.")


def mm_feedback(code, guess):
    black = sum(a == b for a, b in zip(code, guess))
    common = sum(min(code.count(c), guess.count(c)) for c in "ABCDEF")
    return black, common - black


ALL_CODES = ["".join(p) for p in itertools.product("ABCDEF", repeat=4)]


def play(game, secret, N, a, seed):
    rules = GUESS_RULES.format(N=N) if game == "guess" else MM_RULES
    msgs = [{"role": "user", "content": rules}]
    lo, hi = 1, N
    feasible = ALL_CODES[:]
    log = []
    limit = 3 * math.ceil(math.log2(N + 1)) + 5 if game == "guess" else 15
    rejects = n_rej = 0
    if a.verify:
        limit += 15 * a.verify   # loop iterations; only accepted guesses are counted as turns below
    turn_ct = 0
    for turn in range(limit):
        # compact history: older assistant turns are reduced to their GUESS line (all guesses + feedback are kept,
        # only the free-text reasoning of old turns is dropped) so 60-turn games fit in the context window
        view = [m if (m["role"] != "assistant" or i >= len(msgs) - 4) else
                {"role": "assistant", "content": (re.findall(r"GUESS[^\n]*", m["content"]) or ["(no guess)"])[-1]}
                for i, m in enumerate(msgs)]
        try:
            o = chat_msgs(view, think=a.think, max_tokens=a.max_tokens, seed=seed + turn, temperature=0.6)
        except Exception as e:  # e.g. context overflow -> count as a failed game, never crash the whole run
            log.append({"guess": None, "error": str(e)[:200]})
            return {"solved": False, "turns": turn, "log": log, "error": True}
        msgs.append({"role": "assistant", "content": o["text"] or "(no answer)"})
        # parse ONLY the last non-empty line (v1 parsed illustrative example guesses inside strategy essays)
        last = ([l for l in o["text"].strip().splitlines() if l.strip()] or [""])[-1]
        m = re.findall(r"GUESS\s*:?\s*`?\*{0,2}([A-Fa-f]{4}|-?\d+)", last)
        if not m:
            log.append({"guess": None, "finish": o["finish"], "tok": o["out_tokens"]})
            msgs.append({"role": "user", "content": "Invalid format. Reply with one guess on the last line as `GUESS ...`."})
            continue
        g = m[-1].upper()
        if game == "guess":
            if not g.lstrip("-").isdigit():
                msgs.append({"role": "user", "content": "Please guess an integer."}); log.append({"guess": g, "invalid": True}); continue
            x = int(g)
            consistent = lo <= x <= hi
            mid_dev = abs(x - (lo + hi) / 2) / max(1, (hi - lo + 1)) if consistent else None
            log.append({"guess": x, "consistent": consistent, "mid_dev": mid_dev, "width": hi - lo + 1, "tok": o["out_tokens"]})
            if x == secret:
                return {"solved": True, "turns": turn + 1, "log": log}
            if x < secret:
                lo = max(lo, x + 1); reply = "HIGHER"
            else:
                hi = min(hi, x - 1); reply = "LOWER"
            if a.scratchpad:
                reply += f". (State: the secret is now known to be in [{lo}, {hi}].)"
        else:
            consistent = g in feasible
            if not consistent and a.verify and rejects < a.verify:
                rejects += 1; n_rej += 1
                bad = next(e for e in log if e.get("guess") and len(e["guess"]) == 4 and mm_feedback(g, e["guess"]) != mm_feedback(secret, e["guess"]))
                fb_true, fb_if = mm_feedback(secret, bad["guess"]), mm_feedback(g, bad["guess"])
                msgs.append({"role": "user", "content": f"Rejected (not counted): {g} cannot be the secret. Your earlier guess "
                             f"{bad['guess']} got BLACK {fb_true[0]}, WHITE {fb_true[1]}, but if the secret were {g} it would "
                             f"have got BLACK {fb_if[0]}, WHITE {fb_if[1]}. Choose a different guess."})
                continue
            rejects = 0
            log.append({"guess": g, "consistent": consistent, "n_feasible": len(feasible), "tok": o["out_tokens"], "rejects_before": n_rej})
            b, w = mm_feedback(secret, g)
            if b == 4:
                return {"solved": True, "turns": sum(1 for e in log if e.get("guess")), "log": log, "rejections": n_rej}
            if sum(1 for e in log if e.get("guess")) >= 15:
                return {"solved": False, "turns": 15, "log": log, "rejections": n_rej}
            feasible = [c for c in feasible if mm_feedback(c, g) == (b, w)]
            reply = f"BLACK {b}, WHITE {w}"
            if a.scratchpad:
                hist = "; ".join(f"{e['guess']}: B{mm_feedback(secret, e['guess'])[0]} W{mm_feedback(secret, e['guess'])[1]}"
                                 for e in log if e.get("guess"))
                reply += f". (State: all feedback so far: {hist}.)"
        msgs.append({"role": "user", "content": reply})
    return {"solved": False, "turns": limit, "log": log, "rejections": n_rej}


CODE_PROMPT = ("Write a Python 3 program that plays Mastermind as the codebreaker. The secret is 4 pegs; each peg is one "
               "of the colours A, B, C, D, E, F; colours may repeat. Feedback for a guess is BLACK (right colour, right "
               "position) and WHITE (right colour, wrong position). Your program is run once per turn. Input on stdin: "
               "a line with k (the number of previous guesses), then k lines `GUESS BLACK WHITE` (e.g. `AABB 1 2`). It "
               "must print the next guess (4 letters) and nothing else, within 10 seconds. Find the code in as few "
               "guesses as possible using the best strategy. Give the program in a single ```python code block.")


def play_code(secret, a, seed):
    """S-A3: code-as-policy. One program per game, run by the environment every turn."""
    from llm import last_block
    from sandbox import run_python
    msgs = [{"role": "user", "content": CODE_PROMPT}]
    o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, seed=seed, temperature=0.6)
    code = last_block(o["text"], ("python", "py", "python3"))
    feasible, hist, log, repairs = ALL_CODES[:], [], [], 0
    if not code:
        return {"solved": False, "turns": 0, "log": [{"guess": None, "error": "no_code", "finish": o["finish"]}], "code": None}
    for turn in range(15):
        while True:
            stdin = f"{len(hist)}\n" + "".join(f"{g} {b} {w}\n" for g, b, w in hist)
            r = run_python(code, stdin, timeout=20)
            m = re.findall(r"\b([A-Fa-f]{4})\b", r.stdout) if r.status == "ok" else []
            prev = {g_: (b_, w_) for g_, b_, w_ in hist}
            repeat = bool(m) and a.no_repeat and m[-1].upper() in prev
            incons = bool(m) and a.consistent_check and not repeat and m[-1].upper() not in feasible
            if incons:   # S-A3 + behavioural check: a guess the feedback already rules out -> repair (with a counter-example)
                bad_g = next((h for h in hist if mm_feedback(m[-1].upper(), h[0]) != (h[1], h[2])), None)
            repeat = repeat or incons
            if (m and not repeat) or repairs >= a.code_repair:
                break
            repairs += 1   # S-A3 + repair: show the failing input and error, ask for a fixed program (no guess consumed)
            if incons:
                cg = m[-1].upper(); fb_if = mm_feedback(cg, bad_g[0])
                why = (f"it printed {cg}, which cannot be the secret: the earlier guess {bad_g[0]} got BLACK {bad_g[1]}, WHITE "
                       f"{bad_g[2]}, but if the secret were {cg} it would have got BLACK {fb_if[0]}, WHITE {fb_if[1]}; its "
                       f"deduction from the feedback is probably wrong")
            elif repeat:
                rb, rw = prev[m[-1].upper()]
                why = (f"it printed {m[-1].upper()}, which was already guessed (it got BLACK {rb}, WHITE {rw}); repeating a guess "
                       f"gives no new information, so its deduction from the feedback is probably wrong")
            else:
                why = (f"it failed ({r.status}). stderr:\n{r.stderr[-1200:]}" if r.status != "ok" else
                       f"it printed {r.stdout.strip()[:200]!r}, which is not a 4-letter guess")
            msgs += [{"role": "assistant", "content": strip_think(o["text"] or "") or "(empty)"},
                     {"role": "user", "content": f"Your program did not work on this input:\n{stdin}\n{why}\nFix it and give the "
                      "complete corrected program in a single ```python code block."}]
            try:
                o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, seed=seed + repairs, temperature=0.6)
            except Exception:   # context overflow etc.: keep the current program
                break
            code = last_block(o["text"], ("python", "py", "python3")) or code
        if not m:
            log.append({"guess": None, "status": r.status, "err": r.stderr[-200:]})
            return {"solved": False, "turns": turn, "log": log, "code": code, "crash": True, "repairs": repairs}
        g = m[-1].upper()
        log.append({"guess": g, "consistent": g in feasible, "n_feasible": len(feasible)})
        b, w = mm_feedback(secret, g)
        if b == 4:
            return {"solved": True, "turns": turn + 1, "log": log, "code": code, "repairs": repairs}
        feasible = [c for c in feasible if mm_feedback(c, g) == (b, w)]
        hist.append((g, b, w))
    return {"solved": False, "turns": 15, "log": log, "code": code, "repairs": repairs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=1024)
    ap.add_argument("--n_per", type=int, default=15)
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--scratchpad", action="store_true", help="environment restates the state each turn (state-tracking control)")
    ap.add_argument("--games", default="guess,mastermind")
    ap.add_argument("--seed_rep", type=int, default=0, help="replicate index: shifts the sampling seeds (same secrets)")
    ap.add_argument("--verify", type=int, default=0, help="S-A1: reject up to K inconsistent Mastermind guesses per turn, with a counter-example")
    ap.add_argument("--consistent_check", action="store_true", help="S-A3: a guess inconsistent with past feedback triggers a repair")
    ap.add_argument("--no_repeat", action="store_true", help="S-A3: a repeated guess triggers a program repair")
    ap.add_argument("--code_repair", type=int, default=0, help="S-A3: up to R program repairs per game on crash/invalid output")
    ap.add_argument("--code", action="store_true", help="S-A3: the model writes a Mastermind policy program instead of playing")
    a = ap.parse_args()
    rng = random.Random(0)
    jobs = [("guess", rng.randint(1, N), N, 1000 * i) for N in (16, 100, 1000, 10**6) for i in range(a.n_per)]
    jobs += [("mastermind", rng.choice(ALL_CODES), 0, 5000 + 1000 * i + 100000 * a.seed_rep) for i in range(2 * a.n_per)]
    jobs = [j for j in jobs if j[0] in a.games.split(",")]
    out_path = f"{RES}/games_{a.model_tag}.jsonl"
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex, open(out_path, "w") as f:
        for (game, secret, N, seed), res in zip(jobs, ex.map(lambda j: play_code(j[1], a, j[3]) if (a.code and j[0] == "mastermind") else play(j[0], j[1], j[2], a, j[3]), jobs)):
            f.write(json.dumps({"game": game, "N": N, "secret": secret, **res}) + "\n")
    print(f"done {len(jobs)} games in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
