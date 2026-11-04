# Second track: algorithmic components

This folder is for work that needs algorithms, not model training or prompting. Each component plugs into the existing pipeline through
a file format, runs on CPU, and is judged by a pre-registered test in `docs/prereg/PREREG_SIDE.md`. Model runs (GPU) and the
verifier analyses stay in `poc/`, run by the main track.

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

## B. Distinguishing sub-databases for SQL (`poc/sql_witness.py`)

**What for:** when two candidate SQL queries return different rows, a trained pairwise verifier picks one. A witness shows the verifier
why the two queries differ: a few rows of the real database on which they still disagree.

**What it does now:** delta debugging over rows, with foreign keys closed and the results' shape kept as on the real database. It
finds a 1-minimal witness of about 3 rows for most pairs.

**If SIDE-W shows that witnesses help** (see `PREREG_SIDE.md`), the algorithmic work is:
- **Constructed witnesses.** Use constraint solving, as in VeriEQL (OOPSLA 2024) or XData, for pairs whose difference the real data
  shows only on large row sets, or not at all.
- **The most readable witness** among the 1-minimal ones: fewest tables, fewest NULLs, the rows the question names.
- **Speed on 10⁷-row tables.** Use provenance (the rows a query reads) instead of sampling.

**Data:** BIRD (bird-bench.github.io) and Spider (yale-lily.github.io/spider) are public. Develop and test the search on gold queries
against mutated gold queries from BIRD train. The main track runs it on the stored candidate pairs.
