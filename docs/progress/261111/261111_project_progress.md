# Progress 11-03 → 11-12 — *Facts First, Think on Failure*

*Updated 2026-11-13 22:0x UTC. Every number is a pre-registered verdict with a 95% interval. Utility = 100 × correct − 0.5 × output tokens (thousands). The RL study across domains (when a free check can replace labels) is now a separate paper report: `paper/docs/progress/261113/261113_paper_progress.md` (private).*

## At a glance

**In one line:** the model does not solve the puzzle; it only **translates it into code**. A solver counts the solutions. **Exactly one → accept**; otherwise move to a more expensive step (translate while thinking → think only). "Exactly one solution" is a **free check** that needs no labels.

- **Wins:** on ZebraLogic, human-written grids and trip planning, more accurate than thinking alone and usually cheaper, on two model families (Qwen3, gpt-oss).
- **Trained quick step:** using the same free check **as the reward to train the translator with RL** works as well as a gold-label reward, with no labels at all (GridPuzzle +8.4; also +8.8 on gpt-oss-20b); this trained translator is the method's step ①.
- **New this round, the largest gain since RL:** every model drops the same implication, "either A or B" also means A ≠ B. When a translation leaves several solutions, the solver adds that implication and re-counts, with no extra tokens (§3). Held out on four ladders it adds +6 to +15 on GridPuzzle; with it, the grid method beats thinking for every model, including gpt-oss-120b, where it used to tie.
- **Second family as a cheap step (new, held out):** a quick translation by gpt-oss-20b, placed before the expensive thinking translation, settles most puzzles the trained translator leaves open: GridPuzzle 87.8% → **91.0%** at 6.0k tokens, +4.7; Mitra-Baral +4.0 (PREREG_PEERT). With gpt-oss-120b as that step: **92.9% at 4.6k**, +2.6 over gpt-oss-20b (addendum A). Puzzles are computation here: text → constraints → exact solver → free check, like the optimization word problems.
- **Final test on fresh seeds (new):** every step was chosen on seeds 4–9, so the composed method ran once on seeds 14–16, never run before: **GridPuzzle 93.3% at 4.6k tokens vs thinking 60.9% at 11.5k (+35.9); Mitra-Baral 96.5% at 1.2k vs 87.9% at 6.5k (+11.1)** (PREREG_GPF). These are the headline numbers.
- **Remaining weakness, partly closed:** a misreading that still leaves one solution passes the check. Its commonest form is an inclusive "either A or B" plus one constraint no clue states; the closure then leaves no solution, a second free check (+1.8 / +1.4 on fresh seeds, +0.45 held out on four models).
- **Trips:** the gpt-oss-120b quick step holds on fresh seeds for two main models (+3.4, +3.3).
- **Running:** proofs task 1 for the teammate (fresh-figure solver, registered run). Closed this round: the clue check on top of the trained translator (PREREG_GCLF), keeping only the grids both translations allow (PREREG_CONJ), and harder computation (Project Euler, OEIS, MathConstruct).

![Results at a glance](fig/frontier.png)

*Figure 1. Arrow = thinking only (○) → our method (●). Up is more accurate, left is cheaper. ZebraLogic and grids get both; trips are more accurate but spend more tokens.*

| Data | Thinking only → ours | Verdict |
|---|---|---|
| ZebraLogic (750 unseen puzzles) | Qwen3-8B 83.8% → **95.6%**, gpt-oss-20b 76.6% → **99.2%** | Win (+14.0, +26.2) |
| ZebraLogic, the closest paper's 100 puzzles | Qwen3-32B 90.0% → **96.7%** (paper: translation loses) | Win (+9.1) |
| GridPuzzle (human-written grids) | Qwen3-8B 60.9% → **93.3%**, 11.5k → 4.6k tokens (trained translator + gpt-oss-120b quick translation + closure + check; fresh seeds 14–16) | Win (+35.9) |
| Mitra-Baral (small grids) | Qwen3-8B 87.9% → **96.5%**, 6.5k → 1.2k tokens (same) | Win (+11.1 [+5.1, +17.3]) |
| Trip planning (NaturalPlan) | Qwen3-32B 47.0% → **72.0%** (with gpt-oss-120b quick step, fresh seeds) | Utility win (+19.5); check precision below the registered bar |
| GridPuzzle, gpt-oss-120b | 92.3% → **96.9%**, 9.1k → 5.2k tokens (with the closure; 93.1% without) | Win (+6.5) |
| AR-LSAT · BFCL agents | ≈ 0 · loses to a public checkpoint (EnvScaler-8B) | Tie · loss |

---

## 0. Preliminaries

**→ Four ideas carry the report: translate and count solutions, the ladder scored by utility, how precise the check is, and RL with the check as the reward.**

![Preliminaries](fig/prelim.png)

*Figure P. (a) A toy puzzle and four translations of it. The solver counts solutions; only "exactly one" is accepted. The last row shows the known weakness: a sign flip that still leaves one solution. (b) One RL step (GRPO, schematic numbers) used to train step ①: each of 8 samples gets a reward, and its advantage is the reward minus the group mean. The check and gold labels agree except on the "one solution, wrong" sample.*

| Term | Meaning | Example |
|---|---|---|
| Quick translation | the model writes the clues as Python constraints, without thinking (a few hundred tokens) | `p['Bob'] == p['Ann'] + 1` for "Bob lives directly right of Ann" |
| Solution count (the free check) | a solver tries every grid and counts those meeting all constraints; no label needed | 1 → accept; 0 (contradiction) or 2+ (clue lost) → next step |
| Ladder | ① quick translation → ② translate while thinking → ③ think only; stop at the first step that passes | most puzzles stop at ① |
| Utility | 100 × correct − 0.5 × output tokens (thousands); rewards accuracy, charges for tokens | GridPuzzle: ladder 87.3% at 9.1k → 82.8; thinking 63.4% at 11.5k → 57.7 |
| Precision, right : wrong | among answers that pass, the share that is right, and the ratio of right to wrong | GridPuzzle, Qwen3-8B quick answers: 86% right = 6.0 : 1 |
| GRPO | RL that samples a group per question and pushes up samples scoring above the group mean (LoRA r 16, group 8) | Figure P(b) |
| Gold / check reward | reward = right (needs labels) / passes the free check (no labels) | §2 |
| lf / tt | lf: train on other puzzles, test on unseen ones (cross-fitted folds); tt: train on the test puzzles themselves, still without labels | §2 |
| Verdict | registered before the run; paired 95% bootstrap interval over puzzles; **win** = interval above 0, **tie** = it includes 0 | +8.4 [+5.4, +11.5] is a win |

**Data.** ZebraLogic (750 unseen generated puzzles); GridPuzzle (215 human-written grids, 3×4 to 4×6); Mitra-Baral (94 small human-written grids); NaturalPlan trip planning (100). Models: Qwen3-8B / 32B, gpt-oss-20b / 120b, Granite-4.1-8B.

**Experiment names.** GRL = RL with the gold reward · GRLLF = check-only reward · GRLK = pass@k up to 128.

---

## 1. Method: translate, count solutions, think only on failure

**→ The solver does the search, so the bigger the puzzle, the bigger the win.**

![Ladder example](fig/ladder_example.png)

*Figure 2. A real case (GridPuzzle, Qwen3-8B). The quick translation flipped the sign of "4 years before" but still had one solution, so it passed; a clue-by-clue re-read of the grid by the same model caught it.*

| Step | What it does | Accept if |
|---|---|---|
| ① Quick translation | clues → Python constraints, no thinking (a few hundred tokens) | exactly one solution (if several: add the distinctness the either-or clues imply, re-count; §3) |
| ② Another family's quick translation (grids, since 11-13) | gpt-oss-20b translates the same clues, no thinking | the same |
| ③ Translate while thinking | thinking on, translate again | the same |
| ④ Think only | the usual approach | always |

- **Why it wins:** thinking alone collapses on large grids (23% on 4×6) while the ladder keeps 58%. Thinking fails at *search*, not at *reading*.
- **When it wins:** only when the check's precision on the puzzles it accepts beats thinking's accuracy on those same puzzles (derived beforehand, matches measurements). AR-LSAT is the reverse, hence a tie.
- **Prior work:** translation + solver exists (SatLM, Logic-LM). The closest paper (2505.13252) reports that translation loses. **The solution-count gate plus escalation reverses that on their own data** (all 3 models). A SatLM-style gate ("accept if any solution") loses by 4–11 points — the gain comes from the *uniqueness* check.

## 2. Trained quick step: RL on the free check (GRL → GRLLF → GRLK)

**→ Rewarding only "exactly one solution" (no labels) trains as well as the gold reward, and teaches readings the base model never produces even in 128 samples.**

![GRL and GRLLF](fig/u_grllf.png)

*Figure 3. Left: solution count of the first translation; RL mostly turns "0 solutions" (a misread clue makes a contradiction) into correct ones. Right: ladder accuracy vs tokens.*

| Quick step (Qwen3-8B, unseen puzzles) | GridPuzzle ladder | Mitra-Baral ladder |
|---|---|---|
| Base | 69.6%, 18.3k | 88.5%, 9.7k |
| RL, gold reward | 74.7%, 14.4k (+7.0) | 90.8%, 6.7k (+3.8) |
| **RL, check-only reward (no labels)** | **75.8%, 14.0k (+8.4 [+5.4, +11.5])** | 90.2%, 6.9k (+3.2) |
| Think only | 63.4%, 11.5k | 87.1%, 6.3k |

> **Example — reading "a half-hour" as 1.5 (Mitra-Baral lgp-2045).** Clue: *"Tricia came in a half-hour after Ora."*
>
> ```python
> "p['customers:Tricia'] == p['customers:Ora'] + 1.5"   # base: 0 solutions (right in 0 of 128 samples)
> "p['times:Tricia'] - p['times:Ora'] == 0.5"           # RL: one solution, correct (right in 128 of 128)
> ```

- **No labels needed:** check-only − gold = +1.3 [−0.6, +3.3]. The gate and the training signal are the same free check. It also trains a second family, gpt-oss-20b (mixture-of-experts): quick step right on GridPuzzle 60.5% → 69.3% (+8.8 [+5.0, +12.6]), Mitra-Baral +6.4 [+2.8, +9.9], precision 96.3% → 98.0%.
- **No reward hacking:** the share of "one solution but wrong" falls (6.8% → 4.3%). Hypothesis: right readings are rules shared across puzzles, so they rise together; wrong readings that happen to have one solution are puzzle-specific accidents. Rare exception: lgp-2011, where flipping the sign of "2 days **before**" still leaves one solution and passes.
- **What RL leaves, and the clue check on top (PREREG_GCLF):** the same model's clue check catches only 39% of the trained translator's wrong grids (72% before RL), so it adds nothing on GridPuzzle (+0.2 [−0.4, +0.9]; Mitra-Baral +1.9 [+0.2, +4.6]). Half of those wrong grids come from a constraint no clue states (e.g. `p['years:1921'] == p['paintings:Orange Sky']`, which a clue forbids); rejecting them at the gate loses, because the later steps fail on the same puzzles, so the fix belongs in the reward (one expression per clue).
- **Not just sharpening:** even with 128 samples per puzzle the base does not catch up (pass@128 45.1% → 62.8%, +17.7). RL solves 41 of the 118 puzzles the base misses in all 128 samples — the opposite of the math/code finding that the base catches up at large k (2504.13837).
- **Training on the test puzzles themselves** (still no labels) reaches 79.7%, beating thinking on both accuracy and tokens, but the training cost (13–17k tokens per puzzle) cancels the gain → only for answering the same questions repeatedly.
- **Related work:** label-free RL (TTRL majority vote, Co-rewarding, JURY-RL, …) rewards *agreement* among answers. Ours is a *structural* check built into the task: no vote or prover, and its false-pass rate can be measured before training.
- **Further tests** (second family, 32B, majority-vote reward, other domains) belong to the paper report.

## 3. What the free check misses: one dropped convention, and misreadings that still leave one solution

**→ Most of what RL leaves on grids is one convention every model drops, "either A or B" also means A ≠ B. The count already flags it (several solutions), so the solver adds it and re-counts for free: +6 to +15 on GridPuzzle across four models, held out.**

![Distinctness closure](fig/u_dcl.png)

*Figure 4. GridPuzzle accuracy and tokens for thinking (○), the ladder (◆) and the ladder with the closure (●). The top row is where the rule was found; the four rows below were never used to find it (PREREG_DCL).*

> **Example — gp-6671, Qwen3-8B.** Clue 2: *"The camera with a resolution of 24 megapixels is either the $575 model or the Tela G5."*
>
> ```python
> "p['resolutions:24 megapixels'] in (p['prices:575'], p['cameras:Tela G5'])"   # both translators: allows the $575 model to BE the Tela G5 → 2+ solutions
> "p['cameras:Tela G5'] != p['prices:575']"                                      # added by the closure (the two named things are different) → 1 solution, right
> ```

- **How it was found:** where both translations leave several solutions (13.7% of GridPuzzle puzzle-seeds; thinking right on only 31% of them), keeping the grids both allow fails (PREREG_CONJ, +0.0): one set contains the other in 126 of 128 cases, so both translators drop the same thing. Checking the wrongly shared grids against a right translation shows it is one constraint, the distinctness a disjunctive or "neither … nor" clue implies.
- **The rule:** in an `or`, `in`, exclusive-or or "neither" expression, any two named things the expression never equates are different. It is applied **only when the program has several solutions**: the puzzle's one-solution guarantee says the literal reading is too weak exactly then, and a one-solution program is never changed (applying it everywhere breaks 1–8% of right programs).
- **Held out (PREREG_DCL):** GridPuzzle +12.3 / +14.9 / +9.6 / +6.3 (Qwen3-8B, Qwen3-32B, gpt-oss-20b, gpt-oss-120b), Mitra-Baral +0.2 to +3.3, all intervals above 0; 97.9% of the programs it settles are right. The gain did not shrink with model size as I predicted: Qwen3-32B leaves as many ambiguous translations as the 8B model.
- **Limits and prior work:** the rule is a stated convention of this puzzle family, written from reading failures, then confirmed on held-out data. LOGICPO (2506.18383) notes models render the exclusive "either … or" as logical OR; none of the prior work uses the uniqueness guarantee to decide when to strengthen. Open: can the translator learn it without labels? The count reward gives no signal on puzzles where no sample reaches one solution.

**Misreadings that still leave one solution** are the other remaining error. Prompt rules fixed them on ZebraLogic only; for human-written grids we moved to RL (§2).

![Remaining error](fig/u_reading.png)

*Figure 5. Most wrong one-solution programs misread a single phrase ("N houses between") by one position.*

> **Example — ZebraLogic lgp-test-4x4-13.** Clue: *"There are two houses between the one who only drinks water and Peter."*
>
> ```python
> "abs(p['Drink:water'] - p['Name:Peter']) == 2"   # quick translation: two houses between means distance 3 → still one solution, wrong
> "abs(p['Drink:water'] - p['Name:Peter']) == 3"   # after receiving a self-written, checked rule: correct
> ```

| Attempt | Result | Lesson |
|---|---|---|
| Text checks with no model call | catch 0–23% of misreadings | a misread clue still pins down one solution |
| Remember right readings as examples | 85% still misread | examples do not beat the model's habit |
| Model writes a one-sentence rule, kept only if checked (RULE3) | **8% misread, equal to the hand-written fact (+0.9 [−0.9, +3.0])** | hand-written fact removed on ZebraLogic |
| Same method on human-written grids (RULE3G, RULE4) | Mitra-Baral −0.9, −0.3 (fails the no-harm bar) | prompt direction closed → RL |

- The same shape appears in all three domains: "either A or B" in grids, "N houses between" in ZebraLogic, day counting in trips. **A convention every reader shares is invisible to the checks that re-read the answer**; the solution count sees it only when the misreading weakens the clue (several solutions), which is the case the closure fixes.

## 4. Answers to objections

**→ The result survives cheaper consensus, cut-short thinking, other token prices and, with the closure, the strongest thinking model.**

![Baseline comparison](fig/u_baselines.png)

*Figure 6. Against the consensus cascade (MoT). Right: three samples "agree" on the same misreading.*

> **Example — gp-0687, Qwen3-8B.** All three quick translations misread "the four are all different" the same way.
> - Consensus cascade: three identical answers → accept → **wrong**
> - Our ladder: all three have 2 solutions → escalate → translate while thinking gives one solution → **right**

| Objection | Test | Result |
|---|---|---|
| "Accept when several cheap samples agree" (MoT cascade) | same model, threshold most favourable to the cascade | ladder wins GridPuzzle +8.1 / +8.9, trips +9.9 to +16.5 |
| "Just cut thinking short" (thinking budget 1k–8k) | Qwen3's official method | accuracy falls faster than tokens are saved; the best baseline is uncut thinking, and the ladder beats it too |
| "It depends on the token price (0.5)" | recomputed for prices 0–2 | ZebraLogic wins at every price (more accurate and cheaper). With the closure, GridPuzzle is also cheaper than thinking for the trained 8B, 32B and both gpt-oss models; trips are more accurate but costlier, so their utility win holds below 0.4–1.8 points per 1k tokens |
| "Use a stronger thinking model" (gpt-oss-120b) | same grids | without the closure GridPuzzle **tie** (−0.0), Mitra-Baral +1.2; **with it +6.5 [+4.3, +9.0] and +1.8**, at 5.2k tokens against thinking's 9.1k |
| "Learn when to skip step ②" (ESC2) | rule fixed on seeds 1–3, tested on 4–6 | gpt-oss +2.7 / +2.1 but one cell −0.9 → fails. ~200 puzzles cannot guarantee rare rescues |

**Prior methods, re-run on our models and data (PREREG_RW).** Matched rows use the same model, puzzles and seeds; published numbers use other models or subsets, so they are cited, not compared.

| Method | Data | Matched result | Published (other models) |
|---|---|---|---|
| Logic-LM (translate, refine on errors, answer the first solution; Pan et al. 2023) | GridPuzzle · Mitra-Baral, Qwen3-8B, seeds 7–9 | 54.3% · 80.1% (quick translation); 61.9% · 87.6% (thinking translation) against **ours 92.9% · 95.7%** | GridPuzzle paper: GPT-4 5.1% (chain of thought) |
| LINC-style majority of 3 translations | same | 51.2% · 79.8% | — |
| Amonkar et al. formalizer setting, ZebraLogic (their 100) | Qwen3-32B | thinking 90.0% → ours 96.7% (they report translation losing) | — |
| Mixture-of-Thought consensus cascade | GridPuzzle, trips | ladder +8.1 / +8.9, trips +9.9 to +16.5 | — |
| Budget-forced thinking (Qwen3 thinking budget) | all sets | the best baseline is uncut thinking; the ladder beats it | — |
| LLM-Modulo (critics from each trip's structured constraints, up to 10 replans; Gundawar et al. 2024) | trips, Qwen3-32B and gpt-oss-20b, seeds 4–6 | gpt-oss-20b: **LLM-Modulo 96.0% at 29.3k vs ours 82.3% at 26.6k** (ours −12.3 [−18.1, −6.6] utility); Qwen3-32B running | GPT-4o 40.0%, Claude-3.5-Sonnet 47.0%; LLMPC GPT-4o 44.6%; Gemini 1.5 Pro 34.8% (NaturalPlan paper) |

Reading: answering the solver's first solution without counting stays below thinking; the count and the ladder are what make translation pay. On trips LLM-Modulo wins (so far on gpt-oss-20b): its critics are written by hand from every requirement, so a plan that passes them is the trip's plan (288 of 294 passes right); our check is domain-free and only verifies the model's own reading. Being tested now: the same loop with critics the translations already wrote (PREREG_MCRIT).

## 5. Second domain: trip planning

**→ Utility wins, but a model checking its own plans is inaccurate. A different model as checker fixes it, and the checker can be chosen without labels.**

![Trip planning](fig/u_trips.png)

*Figure 7. Trip planning (NaturalPlan). The ladder wins on utility for 3 of 4 models (Qwen3-32B +15.4).*

> **Example — trip 1066 (8 cities, 21 days), a correct plan.** Rule: a travel day counts for both cities.
> - Qwen3-32B as checker (same model as the translator): *"the plan sums to 22 days instead of 21"* ✗ — the same rule misread again
> - gpt-oss-120b as checker: *"Days 4‑6 (inclusive) = 3 days (day 4 counts as travel day)"* ✓

- **The cross-family quick step (PEERT addenda B, B2, fresh seeds 4–6):** gpt-oss-120b's quick translation as step ② adds +3.4 [+0.7, +6.2] to the Qwen3-32B ladder (72.0% vs thinking 47.0%) and +3.3 [+1.1, +5.6] to gpt-oss-20b's; with gpt-oss-20b as the peer it lost (−5.2), so the peer must be precise.
- Precision of one-solution plans is 80–95%, below the registered 95%: misreading the day rule shifts the whole schedule, but the plan stays unique.
- With gpt-oss-120b as checker, 17/18 wrong plans are caught and only 6/196 right ones rejected → **+17.9 [+11.9, +24.1]** over thinking.
- From the verdicts of several checkers alone (no labels), each checker's false-reject rate is estimated within 1.5 points and the best checker is picked.

## 6. Other tracks (briefly)

- **Agents (BFCL):** running three candidates per turn and letting a trained verifier pick beats thinking by +7.1, but loses to the public EnvScaler-8B checkpoint (54.2%). Adding selection on top of it gives nothing → closed.
- **Computation track (40 ideas):** each idea went to its cheapest killing test. Lessons: free checks often accept only puzzles thinking already solves; telling the model about the check makes it satisfy the check instead of re-reading the clue. Two scoring bugs were found in raw outputs and fixed before any verdict.
- **Proofs (teammate guide):** geometry problems → formal language → engine proof → Lean kernel check (all 263 HAGeo proofs pass). Teammate task kit `side/kit_fresh.py`: a solver that finds fresh figures satisfying the hypotheses. Task 1 diagnosed (11-12): the default solver loses 15 problems because random starts rarely land on the solution set (1–8 of 240); walking along the set from the proof's figure gave 8 passing figures on all 41 lost statements in a probe (whole problems 13 → about 20). Those figures sit nearer the proof's own figure, but they still expose planted false steps. The kit now has this as a soundness control (`--control`, 267 plants): the walk counts 0 of them whole and tests every one on 8 figures. Through the kit the walk counts **20 (NL) and 21 (LEAN) whole problems, none lost**, against 13 and 13 for the default solver (reference run; the registered task-1 run is the teammate's). Task 2 kit (`side/kit_h409.py`, 11-13): HAGeo-409 scored from certificates alone (bound to the frozen statement, `geo_check`, 8 fresh figures); reproduces 263 and counts 0 of 737 tampered certificates. Bar: HAGeo 287 (no later result; its code is not public). Measured room: greedy + random portfolio 271; 6 statements do not build; the gap to HAGeo is all below difficulty 5; a longer-CPU run of the same engine is measuring how much is compute.
- **Harder computation (idea 44, closed):** the recipe needs a check built from the problem's own data. Of the three sets tried only Project Euler has one (its statements give small cases with answers, *"you are given S(16) = 19"*). OEIS and MathConstruct were dropped because there the check is written by the same model and shares its misreading (OEIS, 250 easy sequences: thinking 131 right, the checked ladder 120; MathConstruct's own verify() passed 15 constructions, 2 right). On 120 Euler problems the checked ladder ties thinking-then-program at every thinking budget (+2/+1/0/0 problems at 2k/4k/8k/14k). The quick step is either not right or not cheap: Qwen3-8B's quick programs solve 10, nearly all in the easiest band (elsewhere they time out or run out of memory), and Qwen3.5-9B's solve 21 but cost 6.6k tokens, as much as thinking. The stated cases catch misreadings but not errors at scale. Example, pe720: the program reproduces S(4) = 3 and S(8) = 2295 from the statement, then prints 0 for the real input (answer 688081048). Puzzles pay because the solver does the search; on Euler the search is the algorithm the model must invent.

## Next

| Experiment | Question | Depending on the verdict |
|---|---|---|
| **Proofs task 1** (registered run, teammate) | does the teammate's solver reach the reference (20 / 21 whole problems) and pass the soundness control (0 of 267 plants counted)? | if yes, task 1 is done; task 2 (HAGeo-409 coverage, 263 now vs HAGeo 287) next |
| **Proofs task 2** (teammate, kit ready) | portfolio + missing constructions, then HAGeo's rule from the paper, then an algebraic fallback with component choice: more than 287 certified rows at matched CPU? | the course report's proof result |
| **Same engine, 16× CPU** (SIDE-GT-H409-CPU, running) | how much of the gap to 287 is compute? | sets the curve every task-2 lever is scored against |
| **LLM-Modulo on trips** (PREREG_RW B; gpt-oss-20b done: LLM-Modulo ahead by 12.3) | does our generic count match a hand-written domain verifier on Qwen3-32B too? | the report's trip comparison with prior work |
| **Model-written critics** (PREREG_MCRIT, running) | the three paid programs' constraints accept thinking's plans at 95% precision; used as LLM-Modulo critics on the fallback, do they raise the ladder? | if the interval is above 0, fresh seeds 17–19; else LLM-Modulo's edge is stated as its complete hand-written critics |
| **Solver-owned search on trips** (PREREG_NPSAT, queued) | the fallback fails in the model's plan generator; does the CP-SAT interface (the solver searches city orders and days) settle those trips? | if a ladder gains with the interval above 0, fresh seeds 17–19; else the trip residual is stated as the model's reading of a plan's shape |

<details><summary><b>Closed verdicts (22)</b></summary>

| Experiment | Result | Decision |
|---|---|---|
| GPF | composed method once on fresh seeds 14–16: GridPuzzle 93.3% vs 60.9% (+35.9), Mitra-Baral 96.5% vs 87.9% (+11.1) | headline numbers |
| DCLC | closure as a check on one-solution quick programs: +0.45 [+0.20, +0.75] held out (four models), +1.8 / +1.4 on fresh seeds | joins steps ① and ② |
| PEERT-B, B2 | gpt-oss-120b quick step on trips, fresh seeds: +3.4 (Qwen3-32B), +3.3 (gpt-oss-20b) | in the trip method |
| PEERT | gpt-oss-20b quick translation as step ②, held-out seeds 7–9: GridPuzzle +4.7 [+2.8, +7.0], Mitra-Baral +4.0 [+1.7, +6.9]; gpt-oss-120b instead: +2.6 [+0.5, +4.7] more (92.9% at 4.6k) | joins the method; gpt-oss-120b named, gpt-oss-20b on 3090s |
| DCL | distinctness closure on ambiguous translations, held out: GridPuzzle +12.3 / +14.9 / +9.6 / +6.3 (four models), Mitra-Baral +0.2 to +3.3; 97.9% of settled programs right | joins the method (free step inside ① and ②) |
| CONJ | keep the grids both paid translations allow: +0.0; 1 of 128 shares only gold, the sets are nested | out; led to DCL |
| GCLF | clue check on the trained translator: GridPuzzle +0.2 [−0.4, +0.9], Mitra-Baral +1.9 [+0.2, +4.6]; catches 39% of its wrong grids vs 72% before RL | method = trained translator alone |
| GRLLF | check-only reward +8.4 [+5.4, +11.5], vs gold +1.3, precision 93.0% | label-free RL translator is the method; holds on gpt-oss-20b (GRLO +8.8 [+5.0, +12.6]) |
| GRL | gold reward +7.0 [+4.0, +10.2] / +3.8 [+0.3, +7.4] | trained translator as the quick step |
| GRLK | pass@128 +17.7 [+12.6, +23.3], curves never cross | RL teaches new readings |
| RULE3 | vs hand-written fact +0.9 [−0.9, +3.0], 8% misread | hand-written fact removed on ZebraLogic |
| RULE3G · RULE4 | Mitra-Baral −0.9 · −0.3 (fails no-harm bar) | rule method is ZebraLogic-only |
| RULE · RULE2 · CONV | rules fix misreadings but have cold-start and flipped-rule problems; example memory fails | replaced by RULE3 |
| FREE | text checks: precision 91.9–93.3% < 98% | not in the method |
| ZL-AM | wins on the paper's sample for all 3 models (+9.1, +7.4, +20.9) | reverses the paper's conclusion |
| MOT · BUD | consensus cascade and cut thinking both lose to the ladder | §4 |
| GP-120 | gpt-oss-120b GridPuzzle tie | reported as a trend with thinking strength |
| ESC2 | one cell −0.9 | fixed ladder kept |
| Harder computation (Euler, pilot) | checked ladder − thinking +2/+1/0/0 of 120 at 2k–14k (Qwen3-8B); Qwen3.5-9B quick step costs as much as thinking | stays out of the method |

</details>

<details><summary><b>Appendix: setup</b></summary>

- **Model output** (gp-1980, quick translation): `VALUES = [1984, 1988, 1992, 1996]`, `clues = ["p['wines:Friambliss'] - p['types:pinot noir'] == 4", ...]` → converted to CP-SAT, and **all** solutions are counted.
- **Step limits:** ① 4,096 tokens × 3 rounds, ② 16,000 × 3, ③ 32,000. Retry feedback is label-free, one of three messages (run error / 0 solutions / several solutions).
- **Clue check on human-written grids (GC):** the same model compares the accepted grid with the puzzle and names violated clues (~0.9k tokens).
- **RL:** Qwen3-8B LoRA, GRPO, groups of 8, test puzzles split into two folds and cross-fitted (no puzzle is translated by a model trained on it).
- **Evaluation:** every step's tokens are charged. Prompts tuned on dev only, then frozen. Scoring v2 (since 11-11): a cell is right if it names the gold value ("earthquake" = "earthquakes"), same for all arms.

</details>
