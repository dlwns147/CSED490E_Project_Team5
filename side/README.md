# Side project: proofs

The side project is **proofs**: getting exactly right proofs from open models at low cost, in natural language, in Lean, by translation
into a symbolic engine, and by computing an object that proves a statement exists. Everything about it is recorded in this folder, with
the status and the dated log in this file. Decisive runs are pre-registered in `docs/prereg/PREREG_SIDE.md`.

Side work may use the Slurm server's GPUs: a model server and client commands run as one job through `poc/slurm/job.sh` and
`poc/slurm/lane.sh` (see the root `README.md`, section on Slurm).

**Working rules:**
- Work in a fork, or on a branch of this repository. Add files under `side/`, and don't change `poc/` scripts.
- Before any run that decides something, add a pre-registration to `PREREG_SIDE.md`: why, design, predictions, decision. Never edit a
  prediction afterwards; append dated results under it.
- Never commit model outputs, logs, benchmark texts, server addresses or keys. `*.jsonl` and `*.log` are ignored on purpose.
- Read `PROJECT.md` §1 for the goal: exactly right answers at the lowest cost, utility = 100·right − 0.5·(thousand output tokens).

## Where it stands

| Route | State | Hardest open gap |
|---|---|---|
| Geometry by translation (`geo_translate.py`) | Rerunning under a guard, because Newclid derives false facts (see the log) | A prover that is sound and goes beyond DDAR alone: more than one auxiliary point |
| Natural-language proofs | Computational checks of a proof failed (SIDE-PF, SIDE-PG) | A free check that sees a step left unjustified while true, the most common error |
| Lean (main track, `PREREG_PROOF.md`) | A specialised 8B prover is best; the compiler is a perfect check | Not a side-project gap at present |
| Constructions (`construct.py`) | Unsolved for an 8B model; its own checker is not a usable free check | A derived free check, or a search the problem's structure makes exact |

**Running now (geometry, SIDE-GT-SOUND and SIDE-GT-POOL):** single auxiliary points under the guard, then pooling and random pairs, then
the audit on every proof found.

## Log

**2026-11-05 14:5x UTC: DDAR alone survives the guard.** Rerun with `GT_SOUND=1` at 60 s, then read against the earlier run. The audit of these proofs
is still to come.
- Dev: the same 7 translations and 4 problems (IMO 2010 P4, 2014 P4, 2015 P4, 2017 P4).
- Held out: the same 8 translations and 5 problems, of which the same 3 count as faithful (Pan African 2002, Romanian NMO 2006,
  ISL 2012_16).
- Translations whose DDAR run raised an error: 21 → 3 on the held-out set, 5 → 0 on dev.
- So the loss is expected in the auxiliary-point results, whose rerun is running. The withdrawn counts stay withdrawn until it finishes.

**2026-11-05 14:4x UTC: Newclid's proofs are not exact (SIDE-GT-SOUND).** While reading an early proof of ISL 2004 G8, I found CE = DE given as
a premise and AB ∥ CD derived from it, and neither holds in general. Newclid 2.0.2 checks the goal numerically and has an option, off by
default, to check an added statement, so a false fact can spread and "prove" a true goal.
- **Audit** of 68 recorded proofs (`geo_translate.py audit`), every statement tested on its own figure at 1e-4: with plain Newclid, 57
  reran, 16 use a false statement, and 20 rows raised errors. With the guard (`GT_SOUND=1`, every derived fact and merge must hold on the
  run's figure), 47 reran, none uses a false statement, and no row raised an error.
- **Withdrawn until the rerun finishes:** 10 of 65 held-out problems with one auxiliary point, 8 of 65 with no human in the loop, the four
  shortlist problems, and IMO-AG-30's 14 of 30.
- **Still to read:** IMO 2000 P1's proof uses `cong e q p e` with no reason given, though it holds on all 8 fresh figures. A few statements
  fail on some fresh figures where the goal holds, which may be another intersection point.
- Newclid 3.0.1 exists and has not been tried. HAGeo (2512.00097) also has an appendix on a fallacious AlphaGeometry proof of IMO 2020 P1.

**2026-11-05 11:5x UTC: pooling facts across auxiliary points (SIDE-GT-POOL, registered).** Each point runs alone, and every fact it proves about
the figure's own points goes into a pool, fed back as lemmas with no point added. That is k + 1 runs instead of k²/2 pairs. AlphaGeometry2's
SKEST shares facts between trained-model search trees, with no ablation and no run without a language model, so the measurement here is
what sharing adds on its own, with random points. Two faulty runs were stopped, as recorded in the prereg. No verdict yet.

## Proofs (`side/proof_falsify.py`, `side/geo_translate.py`; section C in older records)

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

**Tried on proofs (SIDE-PF dev, 11-04):** a model writes one program per proof that brute-forces the answer on small cases and tests
the proof's concrete claims; a printed counterexample flags the proof.
- On 60 OPC proofs it flagged wrong and right proofs alike: 11 of 30 wrong vs 9 of 30 right (Qwen3-8B, no thinking); 6 vs 5 with
  thinking.
- The false flags come from testing something the proof does not claim: "infinitely many n" tested at one n, values outside the
  hypotheses. Rerunning code cannot fix that, so the proof-level check is dropped.

**A statement alone, before any proof (dev, 11-04; BrokenMath, competition statements perturbed to be false):** reasoning already
separates them.
- Qwen3-8B with thinking, asked "true or false", flags 97% of false statements and 17% of true ones.
- A counterexample program flags 79% and 23%. Requiring both cuts true-statement flags to 7%, at 12.7k tokens.
- Translated to Lean by Qwen3-8B, 67 of 78 statements do not even compile, and Plausible cannot sample ℝ. Not pursued.

**Geometry proofs checked numerically (SIDE-PG dev, 11-04): no recall.** The program drew random instances of the figure and checked
the proof's concrete claims, discarding instances where the problem's own (true) conclusion failed.
- On 57 OPC geometry proofs it flagged 0 of 38 wrong and 0 of 19 right proofs with thinking (12.7k tokens; a third hit the 16k cap).
- The judges name a false geometric fact in only 6 of the 38 wrong proofs; the rest are gaps or missing work, which no numerical
  test sees. Frontier models' proofs of OPC's 22 shortlist geometry problems are right in 2 of 105 cases.

**Geometry by translation and a symbolic engine (SIDE-GT, `side/geo_translate.py`).** The model writes no proof. It
translates the statement into AlphaGeometry's construction language, and Newclid's DDAR (Sicca et al., 2411.11938; CPU) proves it.
- The free check: the problem's conclusion must hold numerically on a random figure built from the translation's hypotheses alone.
  A false goal holds on none; a translation that adds a hypothesis still passes, so faithfulness is read by hand or against a
  reference translation.
- What is known: proving from the construction language is close to solved without a network (HAGeo, 2512.00097: 28 of 30
  IMO-AG-30 on CPU). Translation is the weak link: open models reach at most 46% executable translations even with 54 examples
  (NL2AGBench, 2608.28481). Untested: a small model with this guard and resampling.
- Data: `$POC_DATA/geo/problems.jsonl`, 89 problems (OPC's 22 shortlist geometry problems and 67 from theblackcat102/IMO-geometry),
  11 with an IMO-AG-30 reference; 24 for development, 65 held out.
- Setup: `pip install --no-deps --target $POC_DATA/geo/pylib newclid==2.0.2 colorama networkx pyvis seaborn`; run the check with
  `PYTHONPATH=$POC_DATA/geo/pylib`.
- What we built on top of the guard:
  - repair turns that show the model Newclid's error;
  - `--grammar`: the final line is decoded under an EBNF of Newclid's 81 constructions and their argument counts, using vLLM 0.22's
    `structured_outputs.grammar`;
  - a trivial-goal test that rejects a goal already among the construction's facts;
  - retries on other diagrams when Newclid fails on one (`GT_DDAR_SEEDS`);
  - `aux`, a search over one auxiliary point at a time.
- Results (FINDINGS 11-04; PREREG_SIDE SIDE-GT-H):
  - **Qwen3-8B:** fails as the translator. 1 of 24 dev problems is translated faithfully. The grammar removes the syntax errors,
    but what then passes is trivially true.
  - **Qwen3.6-27B-AWQ** (two 3090s, thinking at medium effort, k = 4, grammar, 2 repair turns):
    - dev: 6 of 24 problems faithful; DDAR proves IMO 2010 P4, 2014 P4, 2015 P4 and 2017 P4;
    - held out (faithfulness judged before any proof attempt): 19 of 65 problems faithful (29%), but DDAR alone proves only 3
      (4.6%; the registered bar of 5 was missed). One of the 3 is ISL 2012 G (2012_16), where frontier natural-language proofs are
      right 0 of 8 times.
  - **gpt-oss-120b:** declines 78 of 96 dev translations as unexpressible. It is faithful on 4 problems, and DDAR proves 1.
- **Correction (11-05, SIDE-GT-SOUND):** counts of proofs here assumed DDAR's proofs were exact; see the log. Run with `GT_SOUND=1`, and audit
  proofs with `geo_translate.py audit`.
- **No human in the loop (SIDE-GT-AGREE):** agreement between independent translations replaces hand reading. On a figure built from one
  translation, the other's construction predicates and goal must hold, both ways. Of 59 translations with blind verdicts, it accepted
  no unfaithful one (0 of 6) and 47 of 53 faithful ones. This check is numerical, so the correction above does not touch it.
- **Auxiliary points from the model (SIDE-GT-AUXP):** Qwen3.6-27B's proposed points proved nothing random points missed, though they found a
  point in fewer tries (695 DDAR calls against 3,514). That was measured with plain Newclid, so it needs rereading under the guard.
- So with a 27B translator the prover is the bottleneck. A project for algorithms work: auxiliary constructions when DDAR stops.
  Our first search is uniform over construction type, then over arguments. HAGeo's heuristics (28 of 30 on IMO-AG-30, random
  constructions 25) are the published target; their code is at github.com/boduan1/HAGeo.

**Other hard proofs, the same question** (OPC graded proofs, wrong / right): is there a free check that sees the common error?

| Area | Free check | OPC (wrong / right) |
|---|---|---|
| Inequalities | numerical minimisation refutes a false step; an SOS certificate proves a polynomial one (LIPS, 2502.13834) | 101 / 93 |
| Functional equations | plug in the claimed solutions; search simple families for missed ones | 190 / 89 |
| Combinatorics | brute force on small cases: the claimed extremum, the claimed construction | 188 / 109 |

None of these sees a step left unjustified while true, the most common error (85% of solutions in IneqMath), so a symbolic engine
that proves, as in geometry, is the stronger route where one exists.

## Constructions: the computation side of proofs (`side/construct.py`; section D in older records)

**Why:** the side work on math runs two ways (user, 11-04): proofs (geometry, above) and computation. A constructive problem
("show that an object with these properties exists") is proved by the object, and whether an object is right is decided by computing.

**Data:** MathConstruct (Balunović et al., 2502.10197; eth-sri/mathconstruct, MIT): 121 competition problems, each with a
human-written verifier and a generator of variations (other parameters, so a remembered answer does not help). Published: o3-mini
(high) 65% of variations; models writing brute-force code 5–10%, and 11–19% when they search small cases and generalise (2024 models,
without thinking). `side/construct.py build` writes two variations of each problem (226 instances of 115 problems; 40 problems for
development, 75 held out).

**Questions:**
1. Which route gives a verified object with the fewest tokens: answer directly (quick or thinking), or write a program that builds or
   searches for the object.
2. Can a checker the model writes from the statement alone, before seeing any answer, stand in for the human verifier as the free
   check? On these problems its false accepts and false rejects are measured exactly. Related: ComBench (2606.10479) has a model
   write verifiers to build a benchmark, then audits them; we found no test-time use.

**Setup:** MathConstruct needs `sympy`, `antlr4-python3-runtime==4.11`, `pydantic`, `loguru`; grading runs with
`PYTHONPATH=$POC_DATA/construct/mathconstruct/src`.

**Results (Qwen3-8B; PREREG_SIDE SIDE-MC-H, 147 held-out instances):**
- One thinking answer with a 30k cap solves 23.1% (22.2k tokens); a 16k cap cuts most runs off (dev: 9 vs 18 right).
- A thinking program solves 18.4%, mostly different instances: the two are right on 27 and 34, only 13 in common.
- The model's own quick checker is not a usable free check. It rejects 28% of right objects, so the registered cascade
  (program, checker, then the answer) is not significantly better than the answer alone (+4.8 points [−0.7, +10.3]).
- Taking the program's object whenever it parses, else the answer, gains +6.8 points [+0.7, +13.5] at 1.4× the tokens. That was
  a secondary arm; it needs a fresh test before anyone relies on it.
- Open question for the teammate: a checker that is right more often than the model's own (written once per problem and checked
  on small cases), or a search program that the problem's structure makes exact.

**For algorithms work:** the program route is search (backtracking, SAT encodings, local search), and "search small cases, find the
pattern, build the large case" is a method of its own.

## Earlier second-track work (no longer the side project)

These two components were built before the side project became proofs. They stay as examples of the interface and as records of what was
tried. Pick either up only as a new proposal.

### Generated agent environments (`side/envs/`, `side/gen_*.py`)

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

### Distinguishing sub-databases for SQL (`poc/sql_witness.py`; closed)

**What it was for:** when two candidate SQL queries return different rows, a trained pairwise verifier picks one. A witness shows the
verifier why the two queries differ: a few rows of the real database on which they still disagree.

**What it does:** delta debugging over rows, with foreign keys closed and the results' shape kept as on the real database. It finds a
witness for 98.4% of the target pairs, with a median of 3 rows.

**Result (SIDE-W, 11-04):** the verifier trained with witnesses equals the one without, in every test set. The witnesses are right and
readable, but the 8B verifier does not use them: its choice changes less than retraining alone changes it. Side project B is closed.
The code stays as an example of a delta-debugging component.
