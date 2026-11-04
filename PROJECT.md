# Project: goal, rules and status

*Solving Problems with LLMs, Accurately and Cheaply.* POSTECH CSED490E, Team 5

This file holds what the project is for, what we found, how we work, and where things stand. The details live elsewhere: setup in
`README.md`, every result (dated) in `docs/FINDINGS.md`, each experiment's predictions and verdict in `docs/prereg/`, and cluster
state in `docs/SLURM_HANDOFF.md`.

## 1. Goal

**Purpose: exactly right answers from LLMs at the lowest cost**, with open models from 8B to 120B, mainly on RTX 3090s (larger
models run tensor-parallel). Every result is reported as accuracy and output tokens; utility = 100 × right − 0.5 × thousand output
tokens.

**Problems are open** (user, 10-30 and 11-05). Any task where an answer can be checked, selected or made exact qualifies. So far:

- computation (geometry, optimization, contest code, SQL);
- tool calls and multi-turn agents;
- instruction following;
- proofs;
- constructions.

New types are welcome after a related-work check.

**Questions are examples, not a boundary:**

- Where should a budget go: thinking, sampling, search, a second model, or tools?
- What tells a right answer from a wrong one? Options:
  - a free check;
  - another model;
  - a verifier trained with labels used only in training;
  - an exact engine after translating into a formal language.
- What should be trained or built when prompting runs out?
- When does a method pay, in theory?

**Methods are open too.** §2 lists what we have so far, not the scope.

## 2. What we found

| Problem | Method and result (prereg IDs in `docs/prereg/`) |
| --- | --- |
| Programs for geometry, optimization and word problems | **The missing fact** (a few lines of exact library usage, or the model's own checked program for a similar problem, found without labels) raises the cheap program in 25 of 29 cells and thinking by +3.5 to +22.6. **A free check, with thinking only on a visible failure**, matches always-thinking accuracy at 30–78% of the tokens where passing programs are right (gpt-oss, Qwen3.5). Where they "leak" (run but are wrong: Qwen3, Nemotron), a 2,000-token think comes first (HO-SB). A failed think gets one retry (+2.5 to +12). The no-label default is short think → full think → retry, 1.7 points below each cell's best over 54 cells; a 30-label pilot does not beat it (PX2). A cross-family peer's quick answer is a good check: Qwen3-8B with gpt-oss-20b on MAMO, 79.8% at 2.1k tokens vs 76.1% at 3.5k (XPEER). |
| Contest code (Codeforces, LiveCodeBench) | A retry on a visible failure transfers (+4.5 / +6.4 over one think). A short think first saves nothing (HO-CC, LC-1). |
| Text-to-SQL (BIRD, Spider) | The check (the query runs and returns rows) is weak: 41–43% of passing quick queries are wrong. The fix: a quick query trained for correctness (plain RL, labels only in training), kept when another model's quick query returns the same rows; otherwise the default; then a trained verifier chooses where the answers disagree. Result: 62.2% at 1.36k tokens vs the default's 59.5% at 1.68k on BIRD dev, confirmed on Spider, which was never used for a decision (CV-1, SEL, SEL-PW, FINAL). |
| Tool calls (BFCL, ACEBench) | Plain RL on the quick calls (+5.1, mostly learning not to call); a call policy fitted on training data; and a verifier that may answer "no call", fitted for the choice it makes. Result: 88.3% vs the default's 83.9% on BFCL. Held out on ACEBench: 80.6% vs 74.0%, +6.5 utility (TC-RL, SEL-TC2-AB, SEL-CL, ACE). |
| Multi-turn agents (BFCL v4, 600 conversations) | **At every turn, the quick turn, the peer model's quick turn and the thinking turn run in sandboxes, and a trained verifier picks one** (MT-SO). Thinking at every step gets 30.8% for Qwen3-8B; this gets 48.8% (Qwen3.5-9B: 38.0% → 53.9%; +17.2 / +15.5 utility). Trained on four of BFCL's eight environment classes and tested on the other four, it still beats thinking by +7.6 / +6.6 utility (MT-SO-ENV). Fixed rules lose: think after an error, think at a request's first step, or a vote. The gain is large because per-turn gains multiply over a conversation; that model has no free parameters and predicts the gain within 2.4 points. |
| Instructions (IFEval, IFBench) | A model-written, executed checker gating thinking beats both modes in 4 of 6 cells (+1.1 to +2.5), at 1.0–2.6× the tokens: a gain, not a saving (IF-1). |
| Short-answer math (MATH-500, AIME) | Text with thinking is best. A program is a second opinion: when text and program agree, 0.3–0.9% are wrong. |
| Lean proofs (miniF2F) | A specialised 8B prover proves the most (Goedel-Prover-V2-8B, 180 of 244). Facts and repair from compiler errors do not help. |
| Geometry proofs (side track, SIDE-GT) | The model translates the statement into a formal construction language, and a CPU engine (Newclid's DDAR) proves it exactly. With Qwen3.6-27B, 4 IMO problems are proved on dev. Held out: 19 of 65 problems are translated faithfully (judged blind). DDAR alone proves 3; adding one random auxiliary point brings it to 10. Four of the 10 are shortlist problems whose graded frontier natural-language proofs are all wrong. Agreement between independent translations certifies faithfulness without reading them: no unfaithful translation passed, and 98% of faithful ones did. With it, 8 of 65 are proved with no human in the loop (SIDE-GT-AGREE). The prover is the bottleneck. |
| Constructions (side track, SIDE-MC) | Unsolved for an 8B model. A thinking answer and a thinking program solve different instances (23% and 18% alone, 33% together). The model's own checker rejects 28% of right objects, so it cannot pick between them. |

**Did not work** (do not retry without a new idea):

- label-free pseudo-labels for choosing the policy: shared mistakes outvote the truth (HO-L, HO-LF);
- self-training with label-free filters (DT3–DT6);
- training the quick answer for the cascade's own reward: it learns to defer or stops abstaining (CV-1, TCRL addenda 2–3);
- verifiers on word problems (SEL-W, VER);
- voting over more quick samples;
- computational checks of natural-language proofs (SIDE-PG, SIDE-PF).

OptMATH is partly broken: its statements omit what its gold answers need.

## 3. Scope

- **Models:**
  - Qwen3 4B–32B, Qwen3.5-9B, Qwen3.6 (27B, 35B-A3B);
  - gpt-oss 20b and 120b, Nemotron-3-Nano, Seed-OSS-36B;
  - the trained baselines STORM and ORLM, run on the same harness.
- **The teammate's second track:** geometry proofs, constructions and generated agent environments. See `side/README.md`; its
  experiments are pre-registered in `docs/prereg/PREREG_SIDE.md`.

## 4. Working rules

1. **Pre-register.** Before a decisive run, write the predictions (with numbers) and a decision rule in `docs/prereg/`. Never edit a
   prediction; append dated results below it.
2. **Do not focus on easy or incremental things** (user, 10-24, 10-29, 11-01, 11-05).
   - Lead with the hard method that could move the frontier, and report it even if it fails.
   - These are not the work:
     - re-analyses, audits and "measure X first" stages;
     - one more task, model, seed set or fresh-instance confirmation;
     - budget reruns, swaps to a bigger model, and post-hoc knob variants;
     - plumbing, re-implemented baselines and write-ups.
   - At every check, first name each track's hardest open gap, and run only what attacks it.
   - Withdraw a planned run that turns out to be incremental, as SIDE-MC-H2 was.
   - **Theory counts as evidence:** derive bounds and optimal policies, and let them shape the designs and the predictions.
   - **No heuristics** (user, 11-01): no hand-set thresholds, orders or cut-offs. A decision rule comes from an explicit model, with
     its parameters estimated and its assumptions tested.
3. **At least 3 seeds** for a positive claim, with 95% intervals over problems. A tie is a tie.
4. **Accuracy with its cost:** always report output tokens.
5. **Read the raw outputs.** Treat a surprising number as a bug until the raw outputs say otherwise.
6. **Record** every result as a dated UTC entry in `docs/FINDINGS.md`. Proposal updates are paused (user, 11-05).
7. **Git:** commit and push after each change. The repository is public: no keys, server addresses or raw outputs (`*.jsonl`,
   logs), and no co-author lines.
8. **Write for a first-time reader:** what ran, the result with its cost, and what is next.

## 5. Status and next steps (2026-11-05)

**Running:**

- **MT-PW** (agents; the hardest open gap). Within a turn, the verifier picks a wrong rollout 11% of the time, often acting where
  the right one asks. Over a conversation that compounds to 11 points of accuracy. A pairwise verifier that sees the alternatives
  is training.
  - The derived alternative, a gate that skips thinking, is dropped: its ceiling is +3.9 utility.

**Next:**

1. MT-PW offline, then online.
2. For geometry, auxiliary points proposed by the model (SIDE-GT-AUXP, running) against random ones.
3. Beyond BFCL: the per-turn choice on τ²-bench. Its protocol is different (a simulated user, policy documents, graded on the
   final database). The BFCL-trained verifier would run zero-shot. This tests the agent-loop claim's external validity; MT-SO-ENV
   only covered environment classes inside BFCL.
4. The final report (`docs/REPORT.md`).

## 6. Documents

| File | Contents |
| --- | --- |
| `README.md` | the manual: setup, running, files |
| `docs/FINDINGS.md` | the lab log: dated, append-only |
| `docs/prereg/PREREG_<id>.md` | one file per experiment: predictions, then results (index: `docs/README.md`) |
| `docs/REPORT.md` | the final-report draft |
| `docs/SLURM_HANDOFF.md` | cluster state, running jobs, environment |
| `side/README.md` | the second track |
| `docs/notes/` | the report outline, self-critique and related work |
| `docs/proposal/` | the proposal and slides (paused) |
