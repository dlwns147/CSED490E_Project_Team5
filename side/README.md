# Second track: algorithmic components

This folder is for the second track: components built around algorithms (search, checks, generators), plugged into the existing
pipeline through a file format and judged by a pre-registered test in `docs/prereg/PREREG_SIDE.md`. Side work may use the Slurm
server's GPUs: a model server and client commands run as one job through `poc/slurm/job.sh` and `poc/slurm/lane.sh` (see the root
`README.md`, section on Slurm).

**Working rules:**
- Work in a fork, or on a branch of this repository. Add files under `side/`, and don't change `poc/` scripts.
- Before any run that decides something, add a pre-registration to `PREREG_SIDE.md`: why, design, predictions, decision. Never edit a
  prediction afterwards; append dated results under it.
- Never commit model outputs, logs, benchmark texts, server addresses or keys. `*.jsonl` and `*.log` are ignored on purpose.
- Read `PROJECT.md` §0 for the goal: exactly right answers with the fewest tokens, utility = 100·right − 0.5·(thousand output tokens).

## A. Generated agent environments (`side/envs/`, `side/gen_*.py`)

**What for:** the multi-turn methods (a verifier choosing among sandboxed turn rollouts) are trained and tested on BFCL v4's 8
environments. A new environment family with algorithmic ground truth is a test no verifier has seen.

**What a family is:**
1. **A class.** Methods are the tools, the state lives in public attributes, `_load_scenario(config)` loads the state, and errors are
   returned as `{"error": ...}`. See `envs/package_manager.py`.
   - A result must depend only on the call and the state before it. Never put counters or call order in a result.
2. **A generator.** It writes BFCL-format items: `id`, `cat`, `system` (BFCL's header plus the function docs), `turns`,
   `initial_config`, `involved_classes`, `ground_truth`.
   - The ground truth of a turn is computed by an algorithm, such as a resolver, a search or a shortest plan, under a policy the
     function docs state.
   - The end state must be unique under that policy. BFCL grades by the end state plus an unordered check of the results.
   - Each request must state the rule it implies (which dependencies, which version, what to clean up), as BFCL's requests do. The
     first version of the package manager left two conventions to the function docs, and no model followed them, thinking or not:
     2.5% right (`PREREG_SIDE.md`, SIDE-ENV results).
   - Keep every request kind at no more than a third of the turns. In the second version (rules stated), half of the turns were
     removals with clean-up, and those capped whole conversations at 17.5% with thinking (SIDE-ENV-2).
   - See `gen_pkg.py` and `gen_cal.py`.

**What a family must show** (from three tries: SIDE-ENV, -2, -3):
- Thinking pays. It did in both families, by +15 to +50 points.
- Qwen3-8B with thinking is right in at least 20% of conversations. Both families missed this: 17.5% (packages) and 15% (calendar,
  one booking, one move and one cancellation per conversation).
  - A conversation is right only if every turn is: with a per-turn right rate q, k turns give about q^k. In the calendar, thinking
    got 14 of 28 bookings, 16 of 21 moves and 8 of 23 cancellations right (each counted until the conversation's first wrong
    turn), so three turns land near 0.5 × 0.76 × 0.35 ≈ 13%.
  - Choose the number of turns and the request kinds from a small pilot's q, so that q^k for Qwen3-8B with thinking falls in
    [20%, 85%].
- An error in a turn tells a right turn from a wrong one no better than on BFCL. Otherwise a check that escalates on errors would
  already do the verifier's job.
  - Measure the error rate of right turns against wrong turns, up to each conversation's first wrong turn (`analyze_env.py`
    prints it), and pre-register it that way.
  - BFCL's anchor (turn 0, `results/conf/mt_sel_rows.jsonl`): Qwen3-8B's quick turns show an error in 33% of right turns and 75%
    of wrong ones; with thinking, 29% and 57%.
  - In the calendar it was 9 of 9 right turns and 35 of 40 wrong ones (quick), because the model guesses ids and room names in the
    same step as the reads. That is less separation than BFCL's. SIDE-ENV-3 counted the share of failures without an error instead,
    a measure that fails a family where errors are everywhere.
3. **The CPU check**, which must pass before any model runs:
   `python side/check_env.py <items.jsonl> <Class=side.envs.module> --negative '<a correct fragment>' '<a mistake>'`.
   - The ground truth must be valid for every item.
   - A deliberate mistake must make most items invalid.

**Ideas for the next families:** each should have real constraints and a policy with one answer. The package manager and the
team calendar (`envs/team_calendar.py`) are closed as test beds, and they are examples of the interface.
- Bank transfers under daily limits and fees: the cheapest valid sequence.
- A warehouse: picking under capacity, shortest route.

Add a "missing parameter" variant: a turn that lacks a needed value has an empty ground truth, and the next turn supplies the value, as
in BFCL's `multi_turn_miss_param`.

**The main track runs** `poc/run_mt.py` and `poc/grade_mt.py` unchanged, with
`MT_CLASSES=<Class>=side.envs.<module> MT_ITEMS=<items>`. Then `python side/analyze_env.py <Class=side.envs.module> <items.jsonl>
<tag>` gives the registered numbers for any family: right and tokens per arm, thinking minus quick with its interval, and, for each
failed conversation, the first turn where its state leaves the ground truth's, which attributes differ there, and whether that turn
showed an error.

## B. Distinguishing sub-databases for SQL (`poc/sql_witness.py`; closed)

**What it was for:** when two candidate SQL queries return different rows, a trained pairwise verifier picks one. A witness shows the
verifier why the two queries differ: a few rows of the real database on which they still disagree.

**What it does:** delta debugging over rows, with foreign keys closed and the results' shape kept as on the real database. It finds a
witness for 98.4% of the target pairs, with a median of 3 rows.

**Result (SIDE-W, 11-04):** the verifier trained with witnesses equals the one without, in every test set. The witnesses are right and
readable, but the 8B verifier does not use them: its choice changes less than retraining alone changes it. Side project B is closed.
The code stays as an example of a delta-debugging component.

## C. Proofs (`side/proof_falsify.py`; being tested)

**What the main track already knows** (`docs/prereg/PREREG_PROOF.md`):
- Lean 4 (miniF2F): the compiler is a perfect check.
  - A specialised 8B prover beats general models (Goedel-Prover-V2-8B 180 of 244 statements, Qwen3.6-35B 133).
  - Hints in the prompt and repair from compiler errors do not help.
  - Many cheap attempts before thinking is the right budget split, and 30 graded statements find it.
- When to stop trying on a statement, from Lean's feedback, is published (2606.04883: −26% compute at matched accuracy), so it is not
  a side project here.

**The gap:** natural-language proofs, where nothing checks a proof for free.
- In the Open Proof Corpus (OPC, 2506.21621; 4,934 proofs by frontier models, graded by humans), the judges' feedback on wrong proofs
  names:
  - a missing justification in 22%;
  - a wrong final answer in 15%;
  - a false claim or a counterexample in 10%;
  - no solution in 5%;
  - nothing at all in 51%.
- Computation can catch only the wrong answers and the false claims.

**Test running (SIDE-PF):** a model writes one program per proof that brute-forces the answer on small cases and tests the proof's
concrete claims on instances. A printed counterexample flags the proof.
- Measured on OPC's human labels: the share of wrong proofs flagged, against the share of right proofs flagged (the check's own
  errors).
- If it catches enough with few false flags, a flag rejects the proof directly; it is not shown to a judge, since SIDE-W found an 8B
  verifier does not use a shown counterexample. Next would be BrokenMath (INSAIT), where models "prove" false statements: the
  statement itself can be tested on small cases.
