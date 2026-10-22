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
