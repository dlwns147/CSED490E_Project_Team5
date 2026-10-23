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
