# Pre-registration CH: does an APPROACH hint help on the 311 contest geometry problems, as a cheap step before high effort?

Written 2026-10-19 15:35 UTC, before any CH run. Results are appended below without editing this section.

**Why.** The recipe's fact (exact library usage) has nothing to fix on contest problems: the programs call no library and the failures are
reasoning errors. Earlier hint-like additions did not help: 8 related geometry helpers (H4: gpt-oss-20b low 37.7 → 33.4%, p = 0.001) and
one statement-retrieved solved problem (N6r, 3 seeds: 120b +1.2, 20b −2.0, both n.s.). Untested: a hint about the APPROACH.

**Data.** The 311 validated problems of CC_SET=full (Codeforces geometry, official + generated tests; 74 flagged as possibly multi-answer;
101 rated ≤ 1800, 210 > 1800). Leakage check (done, 15:2x): no statement contains a 40-character chunk of any reference solution or the
words editorial / tutorial; prompts contain only the statement, the instruction and the hint.

**Arms** (poc/run_cc.py `--tags` / `--plan`, new run tags `<m>_medium_tag` / `<m>_medium_plan`; existing behaviour unchanged).
- TAG: one line `Approach tags: <Codeforces tags minus 'geometry' and '*special'>` after the statement. 255 of 311 problems have such tags;
  the other 56 keep the plain prompt, so their existing medium row (same prompt, same seed) is used. Tags are added by humans after the
  contest: **TAG is an upper bound on what an approach hint can give**, not a method.
- PLAN: first call at LOW effort: the statement + "Do not write any code yet. In at most 200 words, describe the approach ... and the edge
  cases". Cap 2,000 tokens including the low-effort reasoning (gpt-oss returns empty content when the cap is too small to finish
  reasoning; empty plans are counted). Second call at MEDIUM effort: the usual prompt + the plan + "Use this plan unless you find it wrong".
  All plan tokens are charged.
- Both at medium effort, 16k output cap (as the existing medium runs), T 0.7, seeds 1–3 with the same per-problem seed as the medium runs
  (paired). Models: gpt-oss-120b (main, GPU1), gpt-oss-20b (fits one 24 GB GPU; GPU2). poc/queues/queue_s2_ch.sh; poc/analyze_ch.py.
- (a) first attempt: medium + hint vs medium.
- (b) escalation step: medium → gate → [medium + hint → gate] → high (64k), vs N13b (medium → gate → high). Gate = the statement's examples,
  then the problem's approximate brute-force oracle (N5; the model's own low-effort oracle, seed 1), charged as in N13b (only when a program
  that passes the examples must be checked). High = the existing high64k runs of the same seed. If everything fails, the high program is kept.

**Baselines recomputed with poc/analyze_ch.py (same files; 933 problem-seeds per model).**
| | medium | always high (64k) | N13b medium → high |
|---|---|---|---|
| gpt-oss-120b | 56.8% @ 6.8k | 66.2% @ 30.1k | 66.2% @ 24.8k (recorded 66.3% @ 24.7k; one problem-seed differs on oracle re-execution) |
| gpt-oss-20b | 47.1% @ 8.7k | 37.9% @ 47.5k (high hits the 62k cap: p90 = 62k) | 51.9% @ 37.7k |

**Decision rule (from the task, 120b; applied to 20b with its own baselines).** (b) a hint earns its place if it reaches ≥ 66.2% at < 24.7k
tokens per problem, or ≥ 68.3% at ≤ 24.7k. (a) ≥ +3 points over medium at ≤ 1.3 × its tokens. For 20b: (b) ≥ 51.9% at < 37.7k, or ≥ 54.0% at
≤ 37.7k; (a) as for 120b. Statistics: paired exact sign test on discordant problem-seeds (3 seeds pooled), plus the difference on each
seed; **no positive claim unless p < 0.05 and the difference has the same sign on all 3 seeds.**

**Prior art (read).**
- AlphaCode (Li et al., Science 2022, arXiv 2203.07814): tags and ratings are *training-time* metadata; at sampling time AlphaCode feeds
  *random* tags to diversify 100k+ samples; the metadata step is a small part of its ablation chain. AlphaCode 2 also randomises tags.
  Neither measures true human tags as a hint to a reasoning model at fixed effort.
- PlanSearch / IdeaSearch (Wang et al., ICLR 2025, arXiv 2409.03733): natural-language observations / one plan, then code; gains are in
  pass@k through diversity, and the authors report that planning "often hurts pass@1" for several (non-reasoning) models.
- Self-planning code generation (Jiang et al. 2023) and Problem-Solving Guide (Kim et al. 2024: predicting tags as a guide); 2506.22954
  (ICPC/CCPC with DeepSeek-R1: an "Algorithm Ideas" scaffold inside a multi-phase pipeline, no isolated control).
- New here only: hints for a *reasoning* model at a fixed effort, priced in tokens, and used as a cheap step *before* paying for high effort.

**Predictions.**
- CH-P1 (a, 120b): TAG +2.0 points over medium (90% range +0.5 to +3.5) at 0.95–1.10 × its tokens — **below the +3 rule**; PLAN +0.5 (range
  −1.5 to +2.0) at 1.10–1.30 × its tokens.
- CH-P2 (a, 20b): TAG +2.5 (range +0.5 to +4.5); PLAN 0 (range −2 to +2) at 1.1–1.4 × its tokens.
- CH-P3 (b, 120b): TAG step 66.3% @ 24.0k (range 65.5–67.0% @ 23–25k), about a coin flip on the rule; PLAN step 66.0% @ 25.0k — fails the rule.
- CH-P4 (b, 20b): the hint step helps more than for 120b because 20b's high is weak (37.9%): TAG step ≥ 53.0% at ≤ 33k (passes the 20b rule);
  PLAN step ≥ 52.5% at ≤ 35k.
- CH-P5 (where): TAG gains are larger on problems rated > 1800 than ≤ 1800, and ≥ 2/3 of the net gained problem-seeds carry a named-algorithm
  tag (binary / ternary search, two pointers, sortings, dp, divide and conquer, data structures, graphs, shortest paths) rather than only
  math / implementation / brute force.
- CH-P6 (followed; LLM judge gpt-oss-120b low on every hint run, validated by reading 20): the program uses at least one tagged technique in
  ≥ 70% of TAG runs whose tags name an algorithm; the program follows the plan's main approach in ≥ 85% of PLAN runs.
- If TAG helps and PLAN does not, the gain depends on human labels, not on the method — reported as such.
Reported beyond accuracy: token distributions (mean, p90, caps), finish reasons, failure kinds (WA / RE / TLE / no code), rating bands,
unflagged problems, and at least 10 programs whose outcome the hint flipped (both directions).

## Results, gpt-oss-20b (2026-10-19 16:39 UTC; results/h2/ch_analysis_oss20.log; 933 problem-seeds; gpt-oss-120b still running)
| policy | accuracy @ tokens per problem | vs reference (paired, discordant +/−, sign p, per seed) |
|---|---|---|
| medium | 47.1% @ 8.7k | |
| (a) medium + TAG | 49.2% @ 8.2k | vs medium +74 / −54, p = 0.093; +3.9 / +1.9 / +0.6 |
| (a) medium + PLAN | 46.3% @ 9.7k | vs medium +89 / −96, p = 0.66; −2.6 / −0.6 / +1.0 |
| N13b medium → high | 51.9% @ 37.7k | |
| (b) N13b + TAG step | 55.3% @ 38.8k | vs N13b +34 / −2, p < 0.001; +3.2 / +3.2 / +3.9 |
| (b) N13b + PLAN step | 55.0% @ 39.1k | vs N13b +33 / −4, p < 0.001; +2.9 / +4.2 / +2.3 |
| **control (added after seeing the above, not pre-registered): (b) N13b + a plain second medium attempt** (another seed's medium program, no hint) | **54.6% @ 39.2k** | vs N13b +29 / −4, p < 0.001 |
| TAG step vs the plain step | | +27 / −20, p = 0.38; −0.3 / +0.3 / +2.3 |
| PLAN step vs the plain step | | +24 / −20, p = 0.65; −0.6 / +1.3 / +0.6 |
- **(a): neither hint earns its place** (TAG +2.1, not significant, below +3; PLAN −0.8). CH-P2 holds (TAG +2.5 ± 2, PLAN 0 ± 2).
- **(b): both steps fail the decision rule on tokens** (55.3 / 55.0% at 38.8 / 39.1k > 37.7k), and the **control shows why they help at all:
  a second medium attempt with no hint gives most of it** (54.6%, +2.7); the hint adds +0.7 (TAG, p = 0.38) and +0.4 (PLAN, p = 0.65) over it.
  For gpt-oss-20b the step before high works because its high effort is weak (37.9%, cap hits), not because of the hint.
  CH-P4 holds on accuracy (≥ 53.0 / 52.5%) and fails on tokens (≤ 33k / 35k).
- Mechanism, from the raw rows: TAG shortens 20b's reasoning on the 255 tagged problems (code-call tokens 8.7k → 8.1k; 16k cap hits 28.9% →
  21.8%; replies without code 30.3% → 24.4%). Of the 74 problem-seeds TAG gains, 35 were medium replies with no code (cap); of the 54 it
  loses, 16 are TAG replies with no code. Read (4 gained, 4 lost): 250_D (tags ternary search, two pointers): medium ran out of tokens, TAG
  wrote the two-pointer scan the tag names and passes; 932_F (dp, data structures): both write a Li Chao tree, only TAG's is right;
  65_C (binary search) and 13_B (implementation): medium gave no code, TAG finished; losses 989_E and 659_D (twice): TAG hit the cap with no
  code where medium had passed; 199_E: a different tangent construction, WA.
- PLAN: 31% of plans hit the 2,000-token cap (288 / 933) and 40 are empty — the plan step itself is expensive for 20b (1.4k tokens).
- Hint followed (judge gpt-oss-120b low, 20b runs judged so far, validation pending): the program uses a named-algorithm tag in 75% of the
  runs whose tags name one (CH-P6 ≥ 70%: holds so far); it follows the plan in 75% (CH-P6 ≥ 85%: refuted so far).
