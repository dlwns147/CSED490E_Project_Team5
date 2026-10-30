# Project: goal, scope, rules and status

*Solving Computational Math with LLMs, Accurately and Cheaply — Tools, Facts, and Checks.* POSTECH CSED490E (Graduate NLP), Team 5
(Sangjun Lee, Seongbin Park).

This file holds what the project is for and how we work. How to install and run everything: `README.md` (the manual). The argument with
all numbers: `PROPOSAL.md` (Korean: `PROPOSAL_ko.md`). The lab log: `docs/FINDINGS.md`.

## 0. In plain words (problems and what solved them)

| problem | what we found / do |
|---|---|
| The model misuses the library, so its program crashes | Give it the **missing fact**: a few lines of exact usage, or its own checked program for a similar problem (found without labels). Raises the cheap program in 25 of 29 cells. |
| Thinking on every problem is expensive | **Run the program for free and think only when it visibly fails.** Same accuracy at 30–78% of the tokens for models whose passing programs are right (gpt-oss, Qwen3.5). |
| Some models' programs run but are wrong (the "leak": Qwen3, Nemotron, gpt-oss on the hardest word problems) | **Think briefly first** (2,000 tokens; 4,000 for the leakiest models) before writing the program; never lost to one full think in 14 new word-problem / geometry cells and closed the worst one (−16.7 → −0.3); for gpt-oss a medium think cut at 2k instead of low effort ties the think-with-retry at 69–83% of its tokens (HO-OSB); on contest problems the full think is better (−3 points against an uncapped think). |
| Thinking also fails visibly sometimes | **Check every step: think again when the think's program fails** (+2.5 to +12 points); a quick repair instead is not cheaper (HO-TR). |
| No labels to tell a wrong-but-running program | **Compare the quick program with the short-think program**: agreeing ones are right 93–97% of the time, disagreeing ones 19–34% (contest problems). It flags single programs but cannot replace the 30 labels for choosing the policy (HO-LF: shared mistakes outvote the truth). |
| Text-to-SQL: passing quick queries are often wrong, and every untrained cascade only ties the default | **Train the quick query to be right (plain RL, labels only in training) and check it with another model's quick query**: 61.3% at 1.36k tokens vs the default's 59.5% at 1.68k on BIRD dev (CV-1). Trained to gate itself instead, the model learns to defer everything. |
| Every model misreads the same statement (OptMATH) | Unsolved — partly the benchmark: many of its problems omit information the gold answer needs. |

Recipe: give the fact → short think → program → free check → full think only on a visible failure → think again once on failure. Honest
summary: against a baseline that also thinks again on failure, the recipe is the cheap end of a cost–accuracy trade-off, not a free win;
without labels short think first is the default (0.2–1.5 points below each cell's best on five task types; text-to-SQL 0.33), and labels mainly tell a
contest-like task, where one full think should go first, from the rest (PX: 30 labels add about two points of selection noise elsewhere).

## 1. Goal

LLMs can solve computational problems — geometry, combinatorial optimization, contest and word problems — by writing a program.
Programs can be silently wrong, and thinking longer is expensive. **Goal: exactly right answers with the fewest tokens, with open models
from 8B to 120B.** Every result is accuracy *and* tokens. Compute: primarily the RTX 3090 partition (24 GB each; models larger than one GPU
run tensor-parallel over several 3090s in one job), so as not to compete with other users (user, 2026-10-23: no longer limited to 24 GB
models).

**The recipe we test:** write a program → add the missing fact (a few lines of exact library usage, or the model's own checked program for
a similar problem, found with no labels) → run a free check (the program runs; its outputs on moved / rotated / mirrored copies agree; the
statement's examples pass) → when the check visibly fails, one cheap repair turn with the error (word problems), then think harder →
reuse a checked program when the problem repeats. For models whose free check leaks (their passing non-thinking programs are often
wrong), the first program is written after a short think (2,000 tokens, budget forcing; 4,000 only for Nemotron-3-Nano / Qwen3-8B, HO-SB4, and not on three other models, HO-4K; 1k is too short; fixed, not a pilot choice, HO-PB; gpt-oss: medium effort cut at 2k
instead of low effort, HO-OSB) instead of none (HO-SB); the check applies to
every step, so a visibly failed think is retried (HO-CM).

## 2. Main claim and where it stands

**Restated 2026-10-25 (HO-CM):** the comparisons below were against *one* think given the same fact. Given the same free check too —
think again when its program visibly fails (T→T) — thinking gains +2.5 to +12.3 points on the hard word problems at 105–164% of its
tokens, and is more accurate than every cheap-first policy there for every model (e.g. gpt-oss-20b BWOR: fact-first −10.2 [−16.7,
−4.1] at 37% of T→T's tokens). The claim is therefore a frontier: **apply the free check at every step, thinking included.** Over 54
cells of four hybrid-thinking models the best fixed order without labels is short think → full think → retry on a visible failure
(SB→T→T: 1.74 utility points below each cell's best at λ = 0.5; one think: 7.64; T→T: 3.40); the non-thinking program first is on the
frontier where the check holds (Qwen3.5, geometry) and 2–4 points behind on the leaky models' hardest word problems. Where answers are short and two models' errors rarely coincide, another model's cheap answer is the check that makes cheap first pay: on tool calls, cheap answer → a second model's cheap answer agrees → answer, else SB→T→T, beats the default in 2 of 3 models (HO-PA); on SQL it ties T→T at 63–69% of its tokens (SQL-PA); on word problems it saves nothing. The second model must be about as accurate and of another family: the model's own answer with a plan line (it repeats 38–56% of its wrong answers) and a 3B Llama (right too rarely) both lose to it, an 8B Llama ties it (SQL-DV). On SQL the quick query must improve too: plain RL on BIRD train (labels in training only) raises Qwen3-8B's quick query from 46.0% to 50.6%, and with the peer check it beats the default, 61.3% at 1.36k tokens vs 59.5% at 1.68k (+2.0 [+1.1, +2.9] utility, CV-P8); trained instead for the cascade's own value, the model learns to defer everything (CV-1). gpt-oss-20b's gap
(low effort first) closes the same way: a medium-effort think cut at 2k first ties T→T on BWOR / LogiOR at 69–83% of its tokens (HO-OSB).
On Qwen3-32B the order holds unchanged (SB→T→T best in 3 of 4 cells, retry +2.3 to +10.9, cheap-first still −5 to −12; HO-32): the leak
does not shrink with size. On Seed-OSS-36B, a fourth family, it is best in all 4 cells (retry +3.6 to +10.6, cheap-first −6 to −12;
HO-SEED); the model's own trained thinking budget overruns 2,048 tokens and is not a better first step than the forced cut.

Held-out benchmarks, 3 seeds, 95% intervals over problems; always thinking is given the same fact as the recipe (HO-TF, HO-TF2; full
table: `docs/REPORT.md` §5.1):
- **The fact is the main lever.** It raises the cheap program (the label-free library: 25 of 29 cells) and thinking too (+3.5 to +22.6).
- **Thinking only on a visible failure** ties or beats always thinking with the fact on all five unseen benchmarks for gpt-oss-20b and for
  Qwen3.5-9B — a model the recipe was never developed with — at 30–78% of the tokens, and for Qwen3-14B-AWQ on geometry, LogiOR and
  OptMATH. For Qwen3-14B-AWQ on OptiBench / BWOR and for Qwen3-8B on four of five, thinking with the fact is 4–17 points more accurate:
  there the recipe trades accuracy for tokens, because its free check lets wrong programs through. A 2k-token self-review in
  thinking mode as the gate removes that loss: fact-first ties or beats thinking with the fact in all 6 Qwen3 cells, at 70–73% of the
  tokens on OptiBench and the same cost on BWOR / LogiOR, where even a perfect check saves ≤ 12% (HO-VR); on OptMATH and geometry it ties or wins in 3 of 4 more cells and cuts Qwen3-8B's
  geometry loss from −16.7 to −6.6 by catching 20 of its 37 edge-case-only leaks from the statement (HO-VR2). Nemotron-3-Nano, a model
  from another family, leaks like Qwen3 (fact-first −6 to −12 on OptiBench / BWOR / LogiOR); the gate ties or beats thinking with the
  fact in all 5 of its cells, at 94–109% of the tokens (HO-N4).
- **Short thinking first fixes the leak without a review** (HO-SB, SB2, SB3): thinking with the fact cut at 2,000 tokens, full thinking
  only on that program's visible failure, never loses to always thinking with the fact in the 14 cells it was not chosen on (−0.3 to
  +10.1): Nemotron +3.3 to +6.3 at 72–92% of the tokens (more accurate and cheaper than the gate in all 4 word cells), Qwen3 OptMATH +2.3
  / +3.3 at 85–90%, and Qwen3-8B geometry, the last losing cell, −0.3 (at 98%). Against an uncapped (64k) think the accuracy gain
  stays (+4.0 / +4.3) and the saving shrinks to 16–19% (HO-CAP); on contest programming it does not survive (−3.1). It saves tokens where full thinking is long, not where it
  is already short (Nemotron geometry: 137%), and on Qwen3.5 it is more accurate but dearer than the plain recipe.
- **Which to use is detectable:** a 30-label pilot over five policies loses 0.85 points on average over 60 held-out cells, where no fixed
  policy comes within 3.3; on word problems the first escalation is one cheap repair from the error (HO7, HO-N3, HO-R). Without labels,
  the self-review gate is the best fixed policy for the leaky Qwen models (regret 2.52 vs 3.99 for always thinking with the fact; HO-P3).
  On Nemotron-3-Nano the pilot loses 1.05, and two agreeing cheap programs are the best fixed policy (0.80; HO-N4). With short thinking
  first in the menu (HO-P4, 54 cells of the four hybrid-thinking models): always using it loses 1.47 to each cell's best (other fixed
  policies ≥ 5.8), the 30-label pilot 1.19, and the menu gains +2.1 per cell. On the three task types it was not developed on (PX,
  48 cells) the pilot loses 1.29 / 1.96 / 1.77 (contest code / tool calls / instructions) and the no-label default 3.07 / 0.23 / 0.92:
  among ten close policies 30 labels add about two points of selection noise, so they pay only where the default is wrong (contest code,
  where one plain think, 1.24, does as well); 100 labels: 0.25 / 0.74 / 0.82. On 33 cells no pilot had seen (Qwen3-32B-AWQ,
  Seed-OSS-36B, gpt-oss-20b; PX2) the default loses 0.72, the argmax pilot 1.30, a pilot gated on a paired test 0.79: the default is the rule. On text-to-SQL, pre-registered before any row (SQL-1, 9 cells), the
  default loses 0.33, the argmax pilot 2.25; a label-free switch to the check-matched think when the default spends more tokens on 30
  unlabeled questions costs nothing there (0.34); in-sample it closes about 40% of contest code's gap (3.07 → 2.40) but costs
  0.14 on PX2's word cells (0.72 → 0.86): an option for contest-like tasks, not part of the default.
- The label-free library of checked programs raises the first program in 25 of 29 model × benchmark cells (up to +34 points; not on
  BWOR / LogiOR for Nemotron-3-Nano, a model from another family, whose failures there are formulations).
- **Contest programming** (HO-CC, 311 Codeforces geometry problems, hidden tests): the retry on a visible failure transfers (+4.5 /
  +6.4 over one think; +3.1 at 64k); short think first is a trade there (Nemotron, uncapped 64k think: −3.1 at 84% of the tokens); the
  non-thinking program first loses 5–8 points. On general contest code (LC-1 / LC-OSS, LiveCodeBench 2025, four models, three
  families) short think first is never a saving (94–102% of the check-matched think's tokens); the samples leak 11–34% of passing
  non-thinking programs; the non-thinking program first ties one think for Qwen3-8B and Qwen3.5-9B at 87–88% of its tokens (Qwen3.5-9B
  against its think at 64k, the cap rule: 64.3% vs 49.3% at 32k) and loses for Qwen3-14B-AWQ and gpt-oss-20b; the check-matched think
  stays 3.7–5.5 points above it.
- **Text-to-SQL** (SQL-1, BIRD dev 2025-11-06, 1,530 questions, Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B, pre-registered): the free
  check (the query runs and returns rows) is weak — 41–43% of passing non-thinking queries are wrong, it fails 30–36% of wrong ones — so
  the non-thinking query first loses 2.7–5.9 points to one think; the default order ties the check-matched think at 69% (Qwen3.5-9B)
  and 89.7% (Qwen3-14B-AWQ) of its tokens (Qwen3-8B: tie at 91%). Over its 9 cells the no-label default loses 0.33, the 30-label
  pilot 2.25. The fact (SQL-F: a SQLite card and the model's own check-passing queries for similar questions on the same database)
  raises the non-thinking query by 2.8–3.7 points but not the cascade (cheap first still 1.2–3.9 below one think given the fact; the
  default not better with it) and lowers the Qwen3 thinks (−2.1 / −1.0): only 57–61% of the check-admitted library is right, and
  its effect rises with that share — a self-built fact is only as good as the check that admits it (causal, SQL-FA: changing only the
  admission predicts each library's effect within 2 points in 12 / 12 cells; admitted by agreement with the short think, the
  library no longer lowers the thinks, at 86–88% of their tokens).
- **A label-free signal for when the passing cheap program is wrong** (HO-CC CC-P2; exploratory on word problems): run the same
  model's short-think program too and compare outputs (on the test inputs, or the printed value). On 311 contest problems a
  sample-passing non-thinking program that agrees is right 93–97% of the time, one that disagrees 19–34% (word problems: 78% vs 16%);
  it fails where both modes share a wrong formulation (OptMATH). Used as a gate it costs both runs and does not beat short think first.
- Where it stops: short-answer competition math (text + thinking is better; a program is useful as a second opinion) and formal proofs
  (a specialized 8B prover, not a fact).

## 3. Scope

- **In:** computational geometry (CG) and combinatorial optimization (CO) solved by LLM-written programs: generated geometry and
  optimization suites, OR word-problem benchmarks (NL4OPT, IndustryOR, MAMO, OptMATH, OptiBench, BWOR, LogiOR), Codeforces geometry,
  Solomon routing, job-shop scheduling.
- **Widened 2026-10-27 (user):** the project need not stay on computation-only problems. Next directions may take the recipe (missing
  fact → cheap answer → free check → think on a visible failure) to tasks whose checks are not program execution, e.g. instruction
  following with model-written constraint checkers or tool calling with API usage as the fact; each is pre-registered against the
  named prior work first (DART 2606.23181 already covers draft-agreement routing on math / code; Li et al. 2505.11423 selective
  reasoning on instruction following).
- **Models:** gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B (one RTX 3090 each), Qwen3.5-9B and Nemotron-3-Nano-30B-A3B (unseen-model tests; the latter on 4 × 3090s), and larger models on several
  3090s (gpt-oss-120b, Qwen3-32B-AWQ, Qwen3.6-35B-A3B; earlier only references); trained baselines (STORM-Qwen3-4B, ORLM-8B) run on the same harness.
- **Side tracks** (kept short in the report): competition math (MATH-500, AIME), Lean and geometry proofs, factual QA (PopQA).

## 4. Working rules

1. **Pre-register.** Before a run, write the predictions with numbers and a decision rule in `docs/prereg/PREREG_<id>.md`; append results
   below, never edit the predictions.
2. **Only runs that can change the main claim.** Ask first: could this result change what we claim? If not, skip it — no replications or
   baselines for their own sake.
   **Hard method work, not easy or incremental work** (user, 2026-10-29: "don't do just easy or incremental things"). Offline
   re-analyses, audits, one more task type and "measure X first" stages are not the work; they may only serve a method track. Lead with
   the hard, risky method that could move the cost–accuracy frontier, build it, and report it even if it fails.
   **Theory counts as evidence** (user, 2026-10-29): use mathematical / theoretical analysis where it helps, not only empirical tests —
   derive what a method can reach (bounds, decompositions, optimal policies) before or alongside running it, and let the derivation
   shape the design and the pre-registered predictions.
3. **At least 3 seeds** for any positive claim; report seed means and, for comparisons, a 95% interval over problems; call a tie a tie.
4. **Accuracy with its cost:** output tokens per problem always; input tokens where prompts differ in length.
5. **Read the raw outputs**, not only scores; treat a surprising number as a harness bug until the raw programs say otherwise.
6. **Record:** a dated entry (UTC, from `date -u`) appended to `docs/FINDINGS.md` for every result; `PROPOSAL.md` and `PROPOSAL_ko.md`
   updated together, short, numbers edited in place. Slides (`*.pptx`, `poc/make_slides.js`) change only when asked.
7. **Git:** commit and push after each change. The repository is public: scan the staged diff for secrets, never commit raw outputs
   (`*.jsonl`, logs), server addresses or keys; no co-author lines — commits are by the team's account.
8. **Explain for a first-time reader:** what ran, how, the result with its cost, what is next.

## 5. Status and next steps (2026-10-27, 01 UTC)

- **Held-out claim, against thinking given the same fact** (HO-TF, HO-TF2, HO-LG, HO-P2): the recipe is a pure saving for gpt-oss-20b,
  gpt-oss-120b and Qwen3.5-9B, a token-for-accuracy trade for the Qwen3 models on the hardest word problems; a 30-label pilot picks the
  policy within 0.85 points. Stronger check (solution checker, HO-VF) closes the Qwen3 gap but saves tokens only on OptiBench; budgeted
  thinking *always* (HO-TB) is a trade, but budgeted thinking *first*, full thinking on a visible failure, is the fix for leaky models
  and the best no-label default for hybrid-thinking models (HO-SB, SB2, SB3, P4; Nemotron-3-Nano, a new family, HO-N4). The usage-crash rule for adding a fact (21 / 24 on the development base
  models) does not transfer: 5 / 11 on the fine-tuned models, where the card stops paying and the library still pays (WF5), 3 / 8 on a new
  family (HO-N4); the pilot chooses the fact.
- **Direction 1 — proofs, where the check is perfect** (Lean 4 + Mathlib on the cluster; PF, PL1, PL2): cheap attempts dominate thinking
  up to always-thinking's budget, thinking adds the statements sampling never reaches; with tokens priced the best split is short and a
  30-label pilot finds it; Qwen3-8B on the same frontier (PL3) agrees.
- **Direction 2 — the fact in the weights, no labels** (DT, DT-14, DT2): LoRA on 1,127 strict-check-passing programs gives Qwen3-8B /
  Qwen3-14B the library's gain without the library (OptiBench, BWOR), not on unseen problem types; it does not fix the check (fact-first
  with the fine-tuned model still loses to thinking with the fact). Self-training on 3,996 unlabeled problems stays at round 1 with every
  label-free filter tried (self-consistency: harmful; cross-model agreement, agreement + thinking-mode review: neutral; DT3–DT5), and
  training the non-thinking mode on its own short-think programs changes neither accuracy nor leak (DT6): the short think stays at inference.
- **Label-free choice of policy** (HO-L, HO-LF): pseudo-labels from agreement fail both within a mode (1.71 vs 0.57) and across modes
  (2.00 vs 1.35 labelled, 1.74 fixed): shared mistakes outvote the truth where the check's blind spot is shared (geometry degenerate
  inputs, OptMATH formulations). Cross-mode agreement is a per-program leak flag (CC-P2), not a substitute for the 30 labels.
- **Larger model, more families** (HO-32, HO-OSB, HO-SEED): the order holds on Qwen3-32B (best in 3 / 4 cells, leak not
  smaller than at 8–14B), with a medium think cut at 2k on gpt-oss-20b, and on Seed-OSS-36B (ByteDance, a fourth family; best in 4 / 4;
  its trained budget overruns 2,048 tokens in 88–99% of problems and loses to the forced cut in 3 / 4).
- **Instructions (IF-1)**: IFEval / IFBench, 3 models: the model's executed checker (written after a 2k think) gates thinking; it beats both modes in 4 / 6 cells (+1.1 to +2.5) but costs 1.0–2.6× thinking's tokens (the checker costs more than a Qwen3 think and fails 19–47% of right answers; it leaks little, 7–20%); thinking beats a rewrite under the same check in 6 / 6. A gain, not a saving, as on tool calls.
- **Tool calls (TC-1)**: BFCL v4, 3 models: the schema check is weak (9–25% of wrong answers for Qwen3) and thinks are short (0.3k), so
  cheap-first loses to thinking for Qwen3 and the recipe as stated (think, again on a failed check) is a +0.5 to +1.5 gain, not a
  saving. HO-PA (10-29): with another Qwen generation's cheap answer as the check (same calls → accept, else SB→T→T) the default
  becomes a saving: +0.9 / +2.0 utility, more accurate, at 71–73% of its tokens for Qwen3-8B / Qwen3.5-9B (Qwen3-14B-AWQ −0.3 n.s.);
  a second sample of the same model repeats 79–80% of its wrong calls, another model 33–39%. On word problems the same check saves
  nothing (coincidence 56–67%, two cheap programs' cost not repaid). SQL-DV (10-30): the check's independence needs another model
  of about the same accuracy — the own plan-view answer loses 1.6–2.2 utility to the peer (0 / 3), Llama-3.2-3B 0.3–1.0 (0 / 3),
  Llama-3.1-8B ties; a sampling seed shared with the generator makes a self-check a near-copy (DV1 not credited). Sampling confound found (Qwen3.5-9B / Nemotron cut thinks at the harness sampling, full thinks at the card's) and tested (SAMP): Qwen3.5-9B's word-problem saving holds with every thinking arm at a matched preset (+5.3 / +7.2 at 68–74% of the tokens); the preset moves the full think in opposite directions by task (tool calls: the general preset −3–5; long program thinks: the coding preset −5–7 via 32k caps), not the cascade.
- Budget (HO-4K): 4,000 does not carry over to Qwen3-14B / Qwen3.5-9B / Qwen3-32B (mean utility −0.06, 5 / 12 cells); the default stays
  2,000. Open: a fixed 2,000 tokens still costs where full thinking is already short (tool calls, TC-1); the final report (draft
  `docs/REPORT.md`, format / length / deadline from the team).
- **Contest code (LC-1, LC-OSS; 10-28)**: LiveCodeBench 2025, Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B / gpt-oss-20b: the contest
  boundary holds on a second set and a third family (short think first: no saving, 0 / 4); the samples leak (P3 3 / 3, gpt-oss too);
  cheap first ties one think for 2 / 3 Qwen models (LC-P2 holds; Qwen3.5-9B decided against its 64k think, 10-29: −1.3 at 88%, the
  32k cap had flattered it by 2.4 points), a 12–13% saving on easy and medium problems, 3.7–5.5 points below the check-matched think;
  an official-grader artifact (unjoined threads) found and reported as a sensitivity.
- **Text-to-SQL (SQL-1, 10-29)**: BIRD dev, three models: the default order saves (SQL-P3 2 / 3), cheap first does not (P2 0 / 3:
  the check catches 30–36% of wrong queries), the no-label default beats the 30-label pilot (P6) and the token switch is harmless there (P7; in-sample a
  trade, so an option, not the default).
  SQL-F (10-29): the fact raises the cheap query (F1 3 / 3) but not the cascade (F2 1 / 3, F4 0 / 3), the leak stays (F5 0 / 3), and
  it lowers the Qwen3 thinks (F3 1 / 3): the check-admitted library is 57–61% right and its effect tracks that share.
  SQL-FA (10-29): precision, not difficulty, decides what the fact does (FA1–FA4 all hold): right − wrong examples +4.9 to +6.2,
  the composition model fixed from SQL-F predicts 12 / 12 cells within 2 points, and the label-free agreement library removes the
  thinks' loss (+1.8 pooled over the check library). The recipe's SQL library is admitted by agreement with the short think.
  SQL-PA (10-29, 1,338 fresh BIRD-train questions): another model's quick query (~60 tokens) as the check makes cheap first a
  saving against T→T (PA1 3 / 3: +0.5 to +1.6 at 63–69% of its tokens) but not significantly better than the default (PA2 1 / 3):
  an option. A model's second sample repeats 87–90% of its wrong answers (Qwen3), another model 52–62%. HO-PA (offline): the peer
  check then the default is the new no-label default on tool calls (2 / 3), not on word problems (0 / 4). Another family
  (Nemotron) is no less correlated than another Qwen generation (PA4 0 / 3). SQL-AND (10-30, offline): a second check from a
  third family loses to the single peer (SQL train 0 / 3, tool calls 1 / 3): agreement falls with difficulty for all checks
  together, and accepting gains accuracy only where the quick answer is right and the default wrong (3–7% of items).
- **Training the quick mode for the cascade (CV-1, 10-29/30)**: RL (LoRA) on Qwen3-8B's non-thinking mode, BIRD train, tested on
  SQL-1's dev questions. Rewarded with the whole cascade's value (its own answer if it accepts after seeing its query's result, the
  same model's think-with-retry if it defers), the model and the gate-only control both learn to defer everything and end at T→T
  (P1–P7 refuted): a gate pays only if it accepts RW at least π_WR / π_RW = 2.5 times as often as WR, and the in-model gate does not
  (the peer: 3.2); with the gate deferring, the generator gets no gradient (46.1% vs base 46.0%). Plain RL (C1) raises the quick query
  to 50.6%, and C1 → peer check → SB→T→T beats the default, +2.0 [+1.1, +2.9] (addendum 4, P8 / P9 hold; predicted +2.2 from the
  strata). C2's checkpoints along training (CV-P10 / P11: is the collapse the Bayes response throughout?) are running.
- Day-to-day state (running jobs, environment, evidence table): `docs/SLURM_HANDOFF.md`.

## 6. Documents

| File | Contents |
|---|---|
| `PROJECT.md` | this file: goal, claim, scope, rules, status |
| `README.md` | the manual: setup, running, files, harness notes |
| `PROPOSAL.md`, `PROPOSAL_ko.md` | the argument with every number (English, Korean; kept in sync) |
| `docs/FINDINGS.md` | lab log, dated, append-only |
| `docs/prereg/PREREG_<id>.md` | one file per experiment: predictions, then results and verdicts (index: `docs/README.md`) |
| `docs/notes/` | REPORT_OUTLINE (final-report draft), CRITIQUE (self-review), RELATED_WORK, FIX_MAP |
| `docs/SLURM_HANDOFF.md` | state of the work on the Slurm cluster |
| `HANDOFF.md` | the old servers' status log (until 2026-10-20) |
