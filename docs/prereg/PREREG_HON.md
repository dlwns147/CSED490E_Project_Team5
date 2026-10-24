# Pre-registration HO-N: the recipe on a model it has never seen (Qwen3.5-9B)

Written 2026-10-22 23:1x UTC, before any run of this model in the project. Slurm, RTX 3090 (one GPU per job). Results go below.

**Why.** Every held-out claim so far rests on the three models the recipe was developed with (gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B).
Three claims can be tested prospectively on a newer model that also fits one 24 GB GPU: (1) the recipe ties or beats always thinking for
a model whose cheap programs are usually right; (2) 30 labelled problems of a new cell pick the right policy (HO-P: regret 0.87);
(3) the label-free usage-crash census says when *not* to add a fact — never tested, because every new cell so far had usage crashes
≥ 5%. Qwen3.5-9B (bf16, 18 GB without its vision tower) is a newer generation trained heavily on code, so it may rarely misuse solver
libraries, the condition the "do not add" side needs.

**Model and settings.** `Qwen/Qwen3.5-9B`, vLLM with `--language-model-only --max-model-len 20480 --max-num-seqs 32`, frac 0.92. Tag `q35`.
Same harness as the other models: temperature 0.7, top-p 0.95, seeds 1–3; cheap arms without thinking (8,192 tokens; geometry 4,096);
thinking arms with thinking on and a 16,000-token budget (as for the Qwen3 models).

**Data and arms** (all held out, never used with this model):
- OptiBench (605), BWOR (82), LogiOR (92), OptMATH (100): `free` (solver-choice prompt), `freef` (+ the usage card), `formx` (the
  label-free library: the strict-check-passing program of the most similar other problem from the three development models' free
  programs), `thinkfree` (thinking).
- Held-out geometry (overlap, convex, tri, clip; 96 items): `fact` (needed helpers + hint), `think` (thinking), as HO-G.

**Predictions.**
- **HON-P1 (the core rule):** FF with the library (formx; think if the program fails, prints nothing or 'No Best Solution') ties or beats
  always thinking (paired 95% interval upper bound ≥ 0) on ≥ 4 of the 5 benchmarks (geometry: FF with the fact and the MR check), at ≤ 80%
  of its output tokens.
- **HON-P2 (the pilot):** over the 15 cells (5 benchmarks × 3 seeds) the k = 30 pilot of `analyze_hop.py` has mean regret ≤ 1.0 point at
  λ = 0.5.
- **HON-P3 (when not to add a fact; WF3 rule unchanged):** per word-problem benchmark compute on the `free` arm, before any gain is read,
  u = share of programs crashing with a usage exception and n = share failing the free check minus u; **add unless u < 5% and n ≥ 25%.**
  Where the rule says add, the card and the library each raise the free program by ≥ +2 points; where it says don't, each changes it by
  ≤ 0. The calls are recorded below before any accuracy is read; if every cell says add, the "do not add" side stays untested (stated).
- **Budget note (as HO-B):** the share of thinking rows that hit 16,000 tokens is reported, with the worst case of counting them right.

**Decision.** P1 + P2 → the main claim (recipe by default, a 30-label pilot to detect where it loses) holds on an unseen model and family
generation; a P1 failure with P2 holding → the deployable claim is the pilot, not the recipe alone; P2 failing → the pilot claim is
restated as development-only. P3 decides whether the census is a two-sided rule or only an "add" signal.

*Note (2026-10-22 23:1x UTC, before any run): the 10-21 setup check (SLURM_HANDOFF §0) saw Qwen3.5-9B crash mostly on library usage on
10 OptiBench problems, so P3 will most likely test only the "add" side again; P1 and P2 are the main tests.*

**Analyses:** `poc/analyze_ho.py` (HO_SET per benchmark), `poc/analyze_hogc.py` / `poc/analyze_hox.py`-style geometry rows,
`poc/analyze_hop.py q35`, `poc/analyze_which_fix.py --census`, `poc/analyze_budget.py q35`.

## Amendment (2026-10-22 23:3x UTC, after the smoke test, before any main run)
Smoke test (job 1229994, first 8 BWOR problems, seed 1, harness sampling, 16k budget; tag `q35smoke`, not part of the results): the cheap
programs are long (0.9–8.2k tokens: whole data tables written into the code) and crash mostly on `gurobipy` imports and invented solver
attributes; **5 of 8 thinking runs hit the 16k budget with the reasoning still open** (no program). Always thinking would be crippled by
the setting, not by the model, and any recipe win would be an artifact. Changed for every thinking arm of this model, before any main run:
the model card's thinking sampling (temperature 1.0, top-p 0.95, top-k 20, presence penalty 1.5, as used for Qwen3.6 in this project) and
a **32k budget** (`--max-model-len 36864`; the hybrid-attention KV cache holds 73k tokens on a 3090, so it still fits one 24 GB GPU).
Cheap arms unchanged. A second smoke (`q35smoke2`: 8 BWOR + 16 OptiBench problems, thinking only) checks the truncation share; if more
than 25% of its runs still hit 32k, the share is reported and the HO-B worst case decides how to read P1. Predictions unchanged.
Smoke 2 (job 1230037, 2026-10-23 00:1x UTC; tag `q35smoke2`, not part of the results): 1 of 24 thinking runs hits 32k (4%; BWOR 1 / 8,
OptiBench 0 / 16), mean 24.3k tokens on BWOR and 11.8k on OptiBench. Settings kept; main runs submitted (7 jobs: OptiBench one per seed,
BWOR, LogiOR, OptMATH, geometry).
Operations (2026-10-23 01:2x UTC; no setting changed): the seven combined jobs decoded only ~200 tokens/s each (long thinking runs fill
the ~73k-token KV cache, so few requests run at once); they were cancelled after 70 minutes and the work resubmitted as a 22-task array,
one task per arm group and seed (`poc/slurm/hon_array.sh`, `hon_specs.txt`, at most 14 GPUs at once); every arm resumes from its rows.

### HON-P3 calls, recorded before any gain was read (2026-10-23 02:4x UTC; `CENSUS_SETS=optibench,bwor,logior,optmath python poc/analyze_which_fix.py --census q35`, free arm, 3 seeds, no labels)
| cell | u (usage crashes) | fail the check | n (non-usage failures) | call |
|---|---|---|---|---|
| OptiBench Qwen3.5-9B | 19.3% | 42.5% | 23.2% | add |
| BWOR Qwen3.5-9B | 32.1% | 58.1% | 26.0% | add |
| LogiOR Qwen3.5-9B | 31.9% | 69.2% | 37.3% | add |
| OptMATH Qwen3.5-9B | 23.7% | 75.3% | 51.7% | add |
Every cell has u ≥ 5% (the model reaches for `gurobipy` and invents solver attributes, as in the setup check), so again only the "add"
side is tested; the "do not add" side stays untested.

### Results HON-P3 (2026-10-23 02:5x UTC; free / freef / formx, 3 seeds; gain = with fact − free, paired 95% interval over problems)
| cell (call: add) | free | + usage card | + label-free library |
|---|---|---|---|
| OptiBench | 41.8% | +19.1 [+16.6, +21.7] ✓ | +19.7 [+16.6, +22.8] ✓ |
| BWOR | 24.4% | +8.9 [+2.0, +16.3] ✓ | +3.7 [−3.3, +11.0] ✓ |
| LogiOR | 19.2% | +13.4 [+7.2, +19.6] ✓ | +6.5 [−0.4, +13.8] ✓ |
| OptMATH | 8.7% | +8.3 [+3.3, +14.0] ✓ | +13.0 [+7.0, +19.3] ✓ |
- **HON-P3 holds on its "add" side: 8 / 8 calls right** (each fact ≥ +2 points; two library gains have intervals reaching below 0). With
  WF3 the rule has now been right in 18 of 20 prospective points, all on the "add" side; the "do not add" side remains untested (no 24 GB
  model so far makes fewer than 5% usage crashes on these benchmarks). On a new model the hand-written card helps as much as the library
  or more on BWOR / LogiOR — unlike Qwen3-8B, whose card missed the routing library it reaches for (WF3).
Operations (2026-10-23 03:2x UTC; no setting changed): OptiBench thinking ran at ~50 problems per hour per seed (ETA 9 h); those three
tasks were cancelled and the remaining problems split over 9 jobs (`NLOPT_SHARD=i/3` per seed, own shard files, `poc/merge_shards.py`
appends them to the seed's file afterwards; ids already present are skipped).

### Results HON-P1 / P2 and the budget note (2026-10-23 07:3x UTC; `python poc/analyze_hon.py q35`, `python poc/analyze_hop.py q35`; 3 seeds, all rows complete)
| benchmark | FF (library / fact, think on a visible failure) | always thinking (32k) | FF − THINK [95%] | FF's tokens | thinking at the cap · worst case |
|---|---|---|---|---|---|
| OptiBench (605) | 68.3% @ 3.94k | 44.7% @ 13.28k | **+23.5 [+20.8, +26.3]** | 30% | 6.5% · +20.1 [+17.2, +23.0] |
| BWOR (82) | 41.5% @ 13.25k | 30.5% @ 21.46k | **+11.0 [+4.5, +17.1]** | 62% | 20.3% · +3.7 [−3.3, +10.2] |
| LogiOR (92) | 40.6% @ 18.48k | 29.0% @ 23.40k | **+11.6 [+6.2, +17.0]** | 79% | 31.9% · +5.8 [+1.1, +10.9] |
| OptMATH (100) | 27.7% @ 12.97k | 13.3% @ 21.56k | **+14.3 [+7.7, +21.3]** | 60% | 21.0% · +3.0 [−4.3, +10.3] |
| geometry (96) | 88.9% @ 6.34k | 85.1% @ 22.27k | **+3.8 [+0.3, +6.9]** | 28% | 8.0% · −0.7 [−3.1, +1.7] |
- **HON-P1 holds: FF beats always thinking on 5 / 5 benchmarks** (every interval above 0) at 28–79% of its tokens; in the worst case for
  the budget (every capped wrong thinking run counted right) it still ties or beats everywhere.
- **HON-P2 holds:** k = 30 pilot regret 0.81 at λ = 0.5 over the 15 cells (k = 10: 2.65); FF is the best policy in 14 / 15 cells (always
  FF: regret 0.05; always THINK: 17.6).
- Raw (thinking arm): 14–25% of thinking programs crash on library misuse (`'CpModel' object has no attribute 'Solve'`,
  `pywraplp ... has no attribute 'OPTIMAL'`) and 6–32% exhaust 32k tokens before any code — thinking does not supply the missing usage
  knowledge, the fact does (development finding 1, now on a new model).
- **Decision:** the main claim holds on a model and model generation the recipe was never developed with: fact first, think on a visible
  failure beats always thinking on all five held-out benchmarks for Qwen3.5-9B, and the 30-label pilot keeps its regret below one point.

## Addendum HO-N2 (2026-10-23 07:4x UTC, before any run of this model): a second unseen model, from another family
**Why.** Qwen3.5-9B is still a Qwen model; the report's limitation is "one open family plus gpt-oss". Gemma-4-E4B-it (Google; 4B
effective parameters, bf16, a thinking switch in its chat template; tag `g4e`) fits one RTX 3090 and has never been used here. It is much
smaller than the other models, so it also tests whether the pilot catches cells where the recipe loses on an unseen family.
**Protocol:** exactly HO-N as amended (same arms, seeds, data, analyses; cheap arms at the harness sampling, thinking with the model card's
sampling — temperature 1.0, top-p 0.95, top-k 64 — and a 32k budget; `poc/slurm/hon_lane.sh --model g4e ...`). A probe + smoke job first
checks that vLLM serves it and how its thinking is delimited (tags `g4esmoke_*`, not part of the results); a harness fix found there is
recorded here before the main runs.
**Predictions.**
- **N2-P1:** FF ties or beats always thinking (interval upper bound ≥ 0) on ≥ 3 of the 5 benchmarks at ≤ 80% of its tokens (a 4B model's
  cheap programs are right less often, so fewer than for Qwen3.5-9B).
- **N2-P2 (the main test):** the k = 30 pilot's mean regret over its 15 cells is ≤ 1.0 point at λ = 0.5, including any cell where FF loses.
- **N2-P3:** the census calls (recorded before any gain) are right in ≥ 6 of the 8 (cell, fact) points; a "do not add" call, if any, is
  the first prospective test of that side.
**Decision.** P2 holding → the deployable claim (recipe by default, 30 labels to catch its losses) holds across a third model family.
**HO-N2 withdrawn (2026-10-23 07:4x UTC, before any result).** The probe (job 1233792) failed at server start: the image's Transformers
does not know model type `gemma4` (the checkpoint was written with Transformers 5.5.0.dev0). Serving it would mean changing the project's
environment (vLLM 0.22 / Transformers of `nlp_project:261021`) for one model, which changes the harness, so the test is not run. No other
locally available model outside Qwen / gpt-oss has a thinking mode and fits a 24 GB GPU (granite-4.1-8b, Llama-3.1-8B, Mistral-7B have
none), so the report keeps the family limitation, now with Qwen3.5-9B as a second Qwen generation.

## Addendum HO-N3 (2026-10-23 07:4x UTC, before any run): the repair step on the unseen model
**Why.** The report adds one cheap repair turn on a visible failure (crash, no value, 'No Best Solution'; the error shown, no thinking)
before thinking (HO7: +0.7 to +4.0 points over the plain recipe for all three development models on OptiBench / OptMATH, at 84–101% of
its tokens). Qwen3.5-9B's visible failures are mostly library misuse with an explicit Python error, and its thinking is very expensive
(13–23k tokens), so the step should pay more here — or the HO7 result is specific to the development models.
**Run:** `run_repair.py q35 <seed> formx` on OptiBench, BWOR, LogiOR, OptMATH (seeds 1–3, no thinking, 8,192 tokens), one RTX 3090 job
per benchmark; `HO7_CELLS=optibench:formx,bwor:formx,logior:formx,optmath:formx python poc/analyze_ho7.py q35`.
- **N3-P1:** FF-R0 ≥ FF in all 4 cells (seed means) and ≥ FF + 1 point in ≥ 3.
- **N3-P2:** FF-R0 uses ≤ 85% of FF's tokens in ≥ 3 of 4 cells (a repair that runs replaces a 13–23k-token thinking run).
**Decision.** P1 → the repair step joins the recipe as its default first escalation on word problems (with the HO7 evidence); P1 failing →
it stays a development-model observation.

### Results HO-N3 (2026-10-23 08:1x UTC; `HO7_CELLS=... python poc/analyze_ho7.py q35`, 3 seeds)
| benchmark | FF | FF-R0 (one repair on a visible failure, then think) | FF-R0 − FF [95%] | FF-R0 tokens / FF's | repairs that run · right (thinking right on those) |
|---|---|---|---|---|---|
| OptiBench | 68.3% @ 3.94k | 70.5% @ 2.87k | **+2.2 [+1.4, +3.0]** | 73% | 156 / 372 (42%) · 102 (62) |
| BWOR | 41.5% @ 13.25k | 43.5% @ 10.64k | +2.0 [−0.4, +4.5] | 80% | 37 / 124 (30%) · 20 (15) |
| LogiOR | 40.6% @ 18.48k | 46.7% @ 16.25k | **+6.2 [+2.2, +9.8]** | 88% | 44 / 180 (24%) · 32 (15) |
| OptMATH | 27.7% @ 12.97k | 33.7% @ 11.22k | **+6.0 [+3.0, +9.3]** | 87% | 40 / 130 (31%) · 28 (10) |
- **N3-P1 holds** (FF-R0 ≥ FF + 1 in 4 / 4 cells; three intervals above 0). **N3-P2 refuted narrowly** (≤ 85% of FF's tokens in 2 / 4:
  73%, 80%, 88%, 87%) — only 24–42% of repairs run, so most visible failures still go to thinking.
- Where a repair runs it is right far more often than thinking on the same problems (182 vs 102 of 277).
- **Decision:** the repair step joins the recipe as its first escalation on word problems: on a visible failure, one cheap repair turn
  with the error, then thinking. Evidence: HO7 (3 development models, 6 / 6 cells ≥ FF) and HO-N3 (unseen model, 4 / 4 cells ≥ FF + 1).
  On geometry it stays out (HO-G-R).

## Addendum HO-R (2026-10-23 08:1x UTC, before any run): should the default policy repair first, on every held-out word cell?
**Why.** HO-N3 makes one cheap repair the first escalation on word problems, but the HO-P cells of the development models (BWOR / LogiOR
with the library `formx`, OptMATH with the mined example `mips`) have no repair rows (HO6 / HO7 repaired other arms), and on BWOR / LogiOR
repair hurt Qwen3-8B in the exploratory HO6 rows. **Run:** `run_repair.py <m> <seed> formx` on BWOR / LogiOR and `... mips` on OptMATH for
gpt-oss-20b (low effort, as its cheap arms), Qwen3-14B-AWQ, Qwen3-8B, seeds 1–3 (no thinking; RTX 3090, one job per model). Then the
pilot of `analyze_hop.py` with FF-R0 as a fifth policy over all 60 held-out cells (45 HO-P + 15 HO-N).
- **R-P1:** FF-R0 ≥ FF − 0.5 in ≥ 7 of the 9 new cells (exceptions expected only for Qwen3-8B on BWOR / LogiOR).
- **R-P2:** at λ = 0.5, always FF-R0 has a lower fixed regret than always FF over the 48 word-problem cells.
- **R-P3:** the 30-label pilot over the five policies keeps mean regret ≤ 1.0 over all 60 cells.
**Decision.** R-P2 → the default policy on word problems is FF-R0 (the pilot still guards the losing cells); otherwise FF stays the default
and repair is a pilot option.

### Results HO-R (2026-10-23 08:5x UTC; 1,284 repairs, every visible failure with code repaired; `python poc/analyze_hop.py --repair oss20 q14a q8b q35`)
FF-R0 − FF (seed means) in the 9 new cells: gpt-oss-20b BWOR −0.8, LogiOR +1.4, OptMATH +3.0; Qwen3-14B-AWQ BWOR −0.8, LogiOR +2.5,
OptMATH +0.3; Qwen3-8B BWOR −3.6, LogiOR −1.1, OptMATH +0.3 (FF-R0 at 80–104% of FF's tokens).
| λ = 0.5 | always FF | always FF-R0 | 30-label pilot (5 policies) |
|---|---|---|---|
| 48 word cells | 2.85 | **1.22** | |
| of which the 36 development-model cells | 2.10 | **1.62** | |
| all 60 cells (geometry: FF-R0 = FF) | 2.86 | 1.56 | **0.94** (k = 10: 3.03) |
- **R-P1 refuted** (5 / 9 cells ≥ FF − 0.5): on BWOR the repair costs all three development models accuracy (−0.8, −0.8, −3.6), and
  Qwen3-8B also on LogiOR. **R-P2 holds** (always FF-R0 1.22 < always FF 2.85; also on the development models alone, 1.62 < 2.10).
  **R-P3 holds** (0.94 ≤ 1.0). FF-R0 is the best policy in 34 of 60 cells.
- **Decision (as pre-registered):** the default policy on word problems is FF-R0 — one cheap repair on a visible failure, then think —
  with the 30-label pilot to catch the cells where it loses (BWOR; Qwen3-8B). Geometry keeps FF.

## Addendum HO-N4 (2026-10-24 22:3x UTC, before any main run of this model): the complete recipe on a new family
**Why it could change the claim.** Every part of the recipe we would hand a user for a new model — the label-free library, the census
rule, the self-review gate as the no-label default for a leaky model (HO-P3), the 30-label pilot — was evaluated only on models used
while developing it or on Qwen3.5-9B, the same family as the gate's development models. A model from another family and architecture
tests whether the final recipe transfers, not one more point on a frontier. **Model:** NVIDIA-Nemotron-3-Nano-30B-A3B (BF16; hybrid
Mamba-Transformer mixture of experts, 3B active; thinking switch in its chat template), on 4 × RTX 3090 (tensor parallel), tag `n3n`,
never used in this project. A probe (8 BWOR + 16 OptiBench problems, harness check only: chat formats, code extraction, no syntax
errors from non-ASCII text) ran before this addendum and is not part of the results.
**Settings (fixed now).** Cheap arms as every model (T 0.7, top-p 0.95, 8,192 tokens); thinking with the model card's sampling (T 1.0,
top-p 1.0) and a 32k budget, context 45,056 tokens for thinking with the library (as HO-N); the review as HO-VR (2k-token thinking cut,
answer cap 2,048 as HO-VR3). **Arms, 3 seeds:** `free`, `freef`, `formx` on OptiBench (605), BWOR, LogiOR, OptMATH; `formxt` (thinking
with the library) on OptiBench's HO-TF third, BWOR, LogiOR, OptMATH; reviews of the passing `formx` programs and one cheap repair of the
visibly failing ones on the same four; geometry: `fact`, `thinkfact`, reviews of the passing fact programs.
- **N4-P1 (the fact):** the library raises the cheap program (formx − free ≥ +2 points) in ≥ 3 of the 4 word benchmarks.
- **N4-P2 (census):** the rule's calls from the `free` arms, recorded here before any fact arm is read, are right for ≥ 6 of the 8
  (benchmark × card / library) points.
- **N4-P3 (the no-label default):** the gate FF-R+F ties or beats thinking with the fact (paired 95% upper bound ≥ 0) in ≥ 4 of the
  5 cells (four word benchmarks + geometry).
- **N4-P4 (pure saving or trade):** FF+F ties or beats THINK+F in ≥ 3 of 5 cells at ≤ 80% of its tokens (the closest prior is the other
  mixture-of-experts reasoning models, gpt-oss-20b / 120b, where it is a pure saving); reported with the decomposition
  P(pass) × [P(cheap right | pass) − P(think right | pass)] per cell.
- **N4-P5 (the pilot):** the 30-label pilot over the five HO-P2 policies keeps mean regret ≤ 1.0 over the 15 cells (λ = 0.5).
**Decision.** P3 and P5 → the complete recipe (library, gate without labels, pilot with 30) transfers to a new family and the claim
says so; P3 refuted → the gate as the no-label default is stated for the Qwen family only; P4 places the model on the saving or the
trade side and the report's model table gains it either way.

### HO-N4 census calls, recorded before any fact arm was read (2026-10-24 23:2x UTC; `CENSUS_SETS=optibench,bwor,logior,optmath python poc/analyze_which_fix.py --census n3n`)
| cell | u (usage crashes) | fail the check | n (non-usage failures) | call |
|---|---|---|---|---|
| OptiBench `n3n` | 9.7% | 42.7% | 33.0% | add |
| BWOR `n3n` | 10.2% | 57.3% | 47.2% | add |
| LogiOR `n3n` | 10.9% | 62.3% | 51.4% | add |
| OptMATH `n3n` | 14.0% | 72.7% | 58.7% | add |
All four "add" (u ≥ 5% everywhere): N4-P2 is scored on the 8 card / library points (OptMATH's card arm was run as well and is counted).

### Results HO-N4, cheap arms: N4-P1 / P2 (2026-10-24 23:3x UTC; `n3n`, 3 seeds, all rows; gain = with fact − free, paired 95% interval)
| benchmark | free | + usage card | + label-free library |
|---|---|---|---|
| OptiBench (605) | 36.2% @ 512 | +6.1 [+3.6, +8.8] | **+16.3 [+13.1, +19.3]** |
| BWOR | 17.5% @ 1,272 | −3.7 [−9.3, +2.4] | −1.6 [−7.3, +4.5] |
| LogiOR | 18.1% @ 1,322 | **−6.9 [−13.0, −0.7]** | −2.2 [−8.0, +4.0] |
| OptMATH | 6.0% @ 1,702 | −0.3 [−3.7, +3.0] | +3.7 [−1.3, +8.7] |
- **N4-P1 refuted** (the library adds ≥ 2 points on 2 / 4: OptiBench, OptMATH). **N4-P2 refuted** (3 / 8 "add" calls right).
- **Raw.** No harness effect (finish = stop in 96–99%; code extracted in all but 4 of 3,345 rows; no non-ASCII syntax errors). With the
  card the model writes `pywraplp` in 97–99% of programs (free: 46%, with CP-SAT, CVXPY, SciPy and pulp otherwise) and carries CP-SAT
  idioms into it (`OnlyEnforceIf` on a linear constraint, `AddAllDifferent` / `Value` on the linear solver): AttributeErrors on BWOR
  18 → 40 and running-but-wrong programs 66 → 98 of 246. The library moves programs toward the similar problem's solver (CP-SAT on BWOR
  57 → 75) without raising accuracy. Its usage crashes are ~10% in every cell (the census's "add" trigger), but on BWOR / LogiOR the
  failures that matter are formulation errors, which neither fact touches.
- **Reading.** The fact is the lever on OptiBench for this model too (+16.3, the largest library gain on any model there), but on the
  hardest word problems a model from another family gains nothing from either fact; the census rule's "add" side, right 21 / 24 on the
  development families, is right 3 / 8 here. Facts and the rule are stated for the families they were measured on.
