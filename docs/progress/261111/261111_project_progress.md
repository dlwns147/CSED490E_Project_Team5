# Progress 11-03 → 11-12 — *Facts First, Think on Failure*

*Updated 2026-11-13 00:0x UTC. Every number is a pre-registered verdict with a 95% interval. Utility = 100 × correct − 0.5 × output tokens (thousands). The RL study across domains (when a free check can replace labels) is now a separate paper report: `paper/docs/progress/261113/261113_paper_progress.md` (private).*

## At a glance

**In one line:** the model does not solve the puzzle; it only **translates it into code**. A solver counts the solutions. **Exactly one → accept**; otherwise move to a more expensive step (translate while thinking → think only). "Exactly one solution" is a **free check** that needs no labels.

- **Wins:** on ZebraLogic, human-written grids and trip planning, more accurate than thinking alone and usually cheaper, on two model families (Qwen3, gpt-oss).
- **Trained quick step:** using the same free check **as the reward to train the translator with RL** works as well as a gold-label reward, with no labels at all (GridPuzzle +8.4; also +8.8 on gpt-oss-20b); this trained translator is the method's step ①.
- **Remaining weakness:** a misreading that still leaves exactly one solution passes the check. With the strongest thinking model (gpt-oss-120b) the grid gain disappears.
- **Running:** proofs task 1 for the teammate (fresh-figure solver, registered run); a pilot on harder computation (Project Euler, OEIS, MathConstruct) with a budget-forced thinking baseline.

![Results at a glance](fig/frontier.png)

*Figure 1. Arrow = thinking only (○) → our method (●). Up is more accurate, left is cheaper. ZebraLogic gets both; grids and trips are more accurate but spend more tokens.*

| Data | Thinking only → ours | Verdict |
|---|---|---|
| ZebraLogic (750 unseen puzzles) | Qwen3-8B 83.8% → **95.6%**, gpt-oss-20b 76.6% → **99.2%** | Win (+14.0, +26.2) |
| ZebraLogic, the closest paper's 100 puzzles | Qwen3-32B 90.0% → **96.7%** (paper: translation loses) | Win (+9.1) |
| GridPuzzle (human-written grids) | Qwen3-8B 63.4% → **75.8%** (translator trained on the check) | Win |
| Mitra-Baral (small grids) | Qwen3-8B 87.1% → 90.2% | Tie (interval includes 0) |
| Trip planning (NaturalPlan) | Qwen3-32B 47.0% → **68.3%** | Utility win; check precision below the registered bar |
| GridPuzzle, gpt-oss-120b | 92.4% → 92.9% | Tie |
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
| Utility | 100 × correct − 0.5 × output tokens (thousands); rewards accuracy, charges for tokens | GridPuzzle: ladder 75.8% at 14.0k → 68.8; thinking 63.4% at 11.5k → 57.7 |
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
| ① Quick translation | clues → Python constraints, no thinking (a few hundred tokens) | exactly one solution |
| ② Translate while thinking | thinking on, translate again | exactly one solution |
| ③ Think only | the usual approach | always |

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
- **Not just sharpening:** even with 128 samples per puzzle the base does not catch up (pass@128 45.1% → 62.8%, +17.7). RL solves 41 of the 118 puzzles the base misses in all 128 samples — the opposite of the math/code finding that the base catches up at large k (2504.13837).
- **Training on the test puzzles themselves** (still no labels) reaches 79.7%, beating thinking on both accuracy and tokens, but the training cost (13–17k tokens per puzzle) cancels the gain → only for answering the same questions repeatedly.
- **Related work:** label-free RL (TTRL majority vote, Co-rewarding, JURY-RL, …) rewards *agreement* among answers. Ours is a *structural* check built into the task: no vote or prover, and its false-pass rate can be measured before training.
- **Further tests** (second family, 32B, majority-vote reward, other domains) belong to the paper report.

## 3. Remaining weakness: misreadings that still leave one solution

**→ The remaining errors are systematic misreadings of one phrase. Prompt rules fixed them on ZebraLogic only; for human-written grids we moved to RL (§2).**

![Remaining error](fig/u_reading.png)

*Figure 4. Most wrong one-solution programs misread a single phrase ("N houses between") by one position.*

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

- The same shape appears in all three domains: "either A or B" in grids, "N houses between" in ZebraLogic, day counting in trips. **A convention every reader shares is invisible to any free check.**

## 4. Answers to objections

**→ The result survives cheaper consensus, cut-short thinking and other token prices. Only the strongest thinking model ties.**

![Baseline comparison](fig/u_baselines.png)

*Figure 5. Against the consensus cascade (MoT). Right: three samples "agree" on the same misreading.*

> **Example — gp-0687, Qwen3-8B.** All three quick translations misread "the four are all different" the same way.
> - Consensus cascade: three identical answers → accept → **wrong**
> - Our ladder: all three have 2 solutions → escalate → translate while thinking gives one solution → **right**

| Objection | Test | Result |
|---|---|---|
| "Accept when several cheap samples agree" (MoT cascade) | same model, threshold most favourable to the cascade | ladder wins GridPuzzle +8.1 / +8.9, trips +9.9 to +16.5 |
| "Just cut thinking short" (thinking budget 1k–8k) | Qwen3's official method | accuracy falls faster than tokens are saved; the best baseline is uncut thinking, and the ladder beats it too |
| "It depends on the token price (0.5)" | recomputed for prices 0–2 | ZebraLogic wins at every price (more accurate and cheaper). Grids and trips are more accurate but costlier, so the utility win holds below 0.4–1.8 points per 1k tokens |
| "Use a stronger thinking model" (gpt-oss-120b) | same grids | GridPuzzle **tie** (−0.0), Mitra-Baral +1.2. Step ② costs more than the strong model's thinking |
| "Learn when to skip step ②" (ESC2) | rule fixed on seeds 1–3, tested on 4–6 | gpt-oss +2.7 / +2.1 but one cell −0.9 → fails. ~200 puzzles cannot guarantee rare rescues |

## 5. Second domain: trip planning

**→ Utility wins, but a model checking its own plans is inaccurate. A different model as checker fixes it, and the checker can be chosen without labels.**

![Trip planning](fig/u_trips.png)

*Figure 6. Trip planning (NaturalPlan). The ladder wins on utility for 3 of 4 models (Qwen3-32B +15.4).*

> **Example — trip 1066 (8 cities, 21 days), a correct plan.** Rule: a travel day counts for both cities.
> - Qwen3-32B as checker (same model as the translator): *"the plan sums to 22 days instead of 21"* ✗ — the same rule misread again
> - gpt-oss-120b as checker: *"Days 4‑6 (inclusive) = 3 days (day 4 counts as travel day)"* ✓

- Precision of one-solution plans is 80–95%, below the registered 95%: misreading the day rule shifts the whole schedule, but the plan stays unique.
- With gpt-oss-120b as checker, 17/18 wrong plans are caught and only 6/196 right ones rejected → **+17.9 [+11.9, +24.1]** over thinking.
- From the verdicts of several checkers alone (no labels), each checker's false-reject rate is estimated within 1.5 points and the best checker is picked.

## 6. Other tracks (briefly)

- **Agents (BFCL):** running three candidates per turn and letting a trained verifier pick beats thinking by +7.1, but loses to the public EnvScaler-8B checkpoint (54.2%). Adding selection on top of it gives nothing → closed.
- **Computation track (40 ideas):** each idea went to its cheapest killing test. Lessons: free checks often accept only puzzles thinking already solves; telling the model about the check makes it satisfy the check instead of re-reading the clue. Two scoring bugs were found in raw outputs and fixed before any verdict.
- **Proofs (teammate guide):** geometry problems → formal language → engine proof → Lean kernel check (all 263 HAGeo proofs pass). Teammate task kit `side/kit_fresh.py`: a solver that finds fresh figures satisfying the hypotheses. Task 1 diagnosed (11-12): the default solver loses 15 problems because random starts rarely land on the solution set (1–8 of 240); walking along the set from the proof's figure gave 8 passing figures on all 41 lost statements in a probe (whole problems 13 → about 20). Those figures sit nearer the proof's own figure, but they still expose planted false steps. The kit now has this as a soundness control (`--control`, 267 plants): the walk counts 0 of them whole and tests every one on 8 figures. Through the kit the walk counts **20 (NL) and 21 (LEAN) whole problems, none lost**, against 13 and 13 for the default solver (reference run; the registered task-1 run is the teammate's).
- **Harder computation (idea 44, pilot, seed 1; decides nothing yet):** the recipe needs a check built from the problem's own data, and of the three sets tried only Project Euler has one (its statements give small cases with answers, *"you are given S(16) = 19"*). OEIS and MathConstruct are dropped: there the check is written by the same model and shares its misreading (OEIS, 250 easy sequences: thinking 131 right, the checked ladder 120; MathConstruct's own verify() passed 15 constructions, 2 right). On 120 Euler problems Qwen3-8B's quick programs solve 10, nearly all in the easiest band; elsewhere they time out or run out of memory. The stated cases catch misreadings but not errors at full scale (accepted answers of 0, overflow). Matched budget, 40 easiest problems: thinking-then-program 13 right at 4k thinking, the checked ladder 14 — a one-problem edge; in the middle band thinking scales (2→5 of 24 from 2k to 14k) and quick programs get 1. Example, pe720: the program reproduces S(4) = 3 and S(8) = 2295 from the statement, then prints 0 for the real input (answer 688081048). Letting checks test helper functions (progc2) made it worse (accepted wrong programs 4–6 per seed against 2–3). Now: does a stronger cheap model widen the window? Qwen3.5-9B so far: quick programs 20 of 66 against the 8B's 8, but at 5.6k tokens — about the cost of 8B thinking.

## Next

| Experiment | Question | Depending on the verdict |
|---|---|---|
| **Harder computation** (Project Euler, easiest band) | does a checked quick program beat thinking-then-program at matched budget? (8B: a one-problem edge of 40; Qwen3.5-9B running) | if not, harder computation stays out of the method |
| **Proofs task 1** (registered run, teammate) | does the teammate's solver reach the reference (20 / 21 whole problems) and pass the soundness control (0 of 267 plants counted)? | if yes, task 1 is done; task 2 (HAGeo-409 coverage, 263 now vs HAGeo 287) next |

<details><summary><b>Closed verdicts (14)</b></summary>

| Experiment | Result | Decision |
|---|---|---|
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

</details>

<details><summary><b>Appendix: setup</b></summary>

- **Model output** (gp-1980, quick translation): `VALUES = [1984, 1988, 1992, 1996]`, `clues = ["p['wines:Friambliss'] - p['types:pinot noir'] == 4", ...]` → converted to CP-SAT, and **all** solutions are counted.
- **Step limits:** ① 4,096 tokens × 3 rounds, ② 16,000 × 3, ③ 32,000. Retry feedback is label-free, one of three messages (run error / 0 solutions / several solutions).
- **Clue check on human-written grids (GC):** the same model compares the accepted grid with the puzzle and names violated clues (~0.9k tokens).
- **RL:** Qwen3-8B LoRA, GRPO, groups of 8, test puzzles split into two folds and cross-fitted (no puzzle is translated by a model trained on it).
- **Evaluation:** every step's tokens are charged. Prompts tuned on dev only, then frozen. Scoring v2 (since 11-11): a cell is right if it names the gold value ("earthquake" = "earthquakes"), same for all arms.

</details>
