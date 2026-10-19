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

## Results, gpt-oss-120b, and verdicts (2026-10-19 17:46 UTC; results/h2/ch_analysis.log; 933 problem-seeds per model)
| gpt-oss-120b | accuracy @ tokens per problem | vs reference (discordant +/−, exact sign p, per seed) |
|---|---|---|
| medium | 56.8% @ 6.8k | |
| (a) medium + TAG | 58.5% @ 6.6k | vs medium +69 / −53, p = 0.17; +3.9 / +1.9 / −0.6 |
| (a) medium + PLAN (plan tokens included) | **51.0% @ 6.8k** | vs medium +55 / −109, **p < 0.001; −1.6 / −10.3 / −5.5** |
| N13b medium → high | 66.2% @ 24.8k | |
| control: N13b + a plain second medium attempt | 66.8% @ 24.9k | vs N13b +18 / −13, p = 0.47 |
| (b) N13b + TAG step | 67.5% @ 25.3k | vs N13b +19 / −7, p = 0.029 (+1.0 / +2.3 / +0.6); vs the plain step +22 / −15, p = 0.32 |
| (b) N13b + PLAN step | 66.5% @ 26.0k | vs N13b +9 / −7, p = 0.80; vs the plain step +12 / −15, p = 0.70 |
By rating (TAG, 120b): ≤ 1800 85.1 vs 84.2%, > 1800 45.7 vs 43.7%; unflagged problems 62.0 vs 59.6%. PLAN, 120b: ≤ 1800 79.2 vs 84.2%, > 1800
37.5 vs 43.7%. Failure kinds (120b, 933 each): medium WA 318 / RE 42 / TLE 6 / no code 37; PLAN WA 400 / RE 32 / TLE 2 / no code 23; TAG (765
runs on tagged problems) WA 247 / RE 36 / TLE 5 / no code 24. Tokens: TAG mean 6.5k (p90 11.9k, 24 cap hits / 765); PLAN 6.8k in total = plan
1.4k (247 of 933 plans hit the 2,000-token cap, 10 empty) + a SHORTER code call (5.2–5.5k vs medium 6.7–6.8k).

**Verdicts against the decision rule.**
- **(a) first attempt: no hint earns its place for either model.** TAG +1.7 (120b, p = 0.17) and +2.1 (20b, p = 0.09) — below +3 and not
  significant (one seed negative for 120b). PLAN *hurts* gpt-oss-120b by 5.8 points (p < 0.001, all three seeds negative) and does nothing for 20b.
- **(b) escalation step: no hint earns its place.** 120b TAG reaches 67.5% but at 25.3k (> 24.7k) and below 68.3%; 120b PLAN 66.5% @ 26.0k;
  20b TAG / PLAN 55.3 / 55.0% at 38.8 / 39.1k (> 37.7k). Against a plain second medium attempt (the control added after the 20b results)
  neither hint is significantly better for either model (p = 0.32–0.70).
- **Tags help a little, the model's own plan does not (it hurts the stronger model): what gain there is depends on human labels, not on the
  method.**
- Predictions: CH-P1 holds for TAG (+1.7 within +0.5…+3.5, 0.97× tokens), **refuted for PLAN** (−5.8, outside −1.5…+2.0). CH-P2 holds. CH-P3:
  TAG step 67.5% @ 25.3k is above the predicted range in accuracy and above it in tokens; PLAN step holds (fails the rule). CH-P4: accuracy holds,
  tokens refuted (see the 20b section). CH-P5 holds: TAG gains are larger above 1800 (+2.0 vs +0.9 for 120b; +2.9 vs +0.7 for 20b), and the
  net gain comes from named-algorithm tags (120b: net +18 named vs −2 for math / implementation / brute force / greedy / constructive;
  20b: +17 vs +3). CH-P6: TAG followed 72% (120b) / 75% (20b) of runs whose tags name an algorithm (holds, ≥ 70%); PLAN followed 75% / 75%
  (refuted, ≥ 85%). Followed hints pass more often (120b PLAN: 59% followed vs 33% deviated; TAG 58% vs 46%).
- Judge validation: I read 20 verdicts (12 from 20b, 8 from 120b, stratified yes / no); 18 agree with my reading, 2 are borderline
  ('brute force' for a 6-face loop; bisect used for coordinate compression under a 'binary search' tag), none clearly wrong.

**Why PLAN hurts gpt-oss-120b (raw programs).** The medium coder trusts the low-effort plan: its own reasoning shortens by about 1.4k tokens,
WA rises from 318 to 400, and a wrong plan is implemented faithfully — 1156_A (Inscribed Figures): the plan counts "n + 1 basic points" and a
wrong special case; the program follows it and fails where plain medium passed. Truncated plans explain only 6–15 of each seed's 29–44 losses.
Gains are real but fewer: 1158_D / 1359_F, where the plan fixed the greedy direction or the meeting-time model.
**What TAG flips (120b, read 3 + 3).** Gains: 1159_F (greedy) — the tagged greedy picks the extreme point correctly where medium's did not;
933_C (graphs) — the tag points to Euler's formula on the planar graph of circle intersections; 535_E (math, uninformative tag) — both build
the same hull, only the tagged run's integer comparison is right (sampling luck). Losses: 23_D a syntax error (`dot(p,p])`), 820_B a different
index formula, 136_D a wrong rectangle test — none caused by the tag.

## CH-R: retry at medium with the free check instead of high effort (gpt-oss-20b) — found offline, pre-registered for fresh seeds (2026-10-19 17:47 UTC)
Exploratory finding on seeds 1–3 (offline, not pre-registered): for gpt-oss-20b, whose high effort is weak (37.9% @ 47.5k, cap hits), up to
three medium attempts (seeds s, s+1, s+2), accepting the first that passes the check (examples, then the brute-force oracle; oracle charged
once), else keeping the last, reaches **55.9% @ 20.7k** — above N13b (51.9% @ 37.7k) at 55% of its tokens; up to two attempts 52.8% @ 15.6k;
with high as the last resort 56.7% @ 41.7k. For gpt-oss-120b high stays the better last step (3 medium attempts, keep last: 62.9% @ 15.0k vs
N13b 66.2% @ 24.8k). The three attempts were also the data the policy was found on, so it is tested on fresh samples:
gpt-oss-20b medium seeds 4–8 (same prompt and settings; poc/queues/queue_s2_chretry.sh, GPU1 + GPU2).
- R-P1: on seeds 4–6 (each seed s uses attempts s, s+1, s+2 within 4–6), up to 3 attempts, keep the last: ≥ 54.0% at ≤ 23k tokens per problem
  (vs medium alone on the same seeds, and vs N13b's 51.9% @ 37.7k on seeds 1–3).
- R-P2: with 5 attempts (seeds 4–8) the gain over 3 attempts is ≤ +1.5 points at ≥ +4k tokens (diminishing returns: the check, not the
  number of tries, is the limit; 24–37% of wrong programs pass the examples).
- R-P3: the oracle-checked retry is what matters: the same 3 attempts accepting on the examples alone are ≥ 1.5 points lower.
