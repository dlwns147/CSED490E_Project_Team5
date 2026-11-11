# PREREG_NPC: the grid clue check on trips, registered 2026-11-10 21:1x UTC, before any check has run on a trip

**Why.** PREREG_NP's gate failed its precision test on trips (P1: Qwen3-32B 90.7% < 95%; see its "Result" section). Read in the programs, 7 of Qwen3-32B's 11 wrong thinking-translation passes start each stay the day after the previous one ends, against the convention stated in the task. That shifts the whole plan and leaves exactly one plan, so a count cannot see it. A count catches a misreading only when the misreading changes the number of answers.

On logic grids the same problem was met by the clue check of PREREG_GC (idea 28). The same model, with thinking, is shown the solver's answer and checks it against the text, and a flag sends the step down the ladder. It held there (GridPuzzle unflagged precision 95.4%, Mitra-Baral 99.2%), and it is the gate's registered second part. A misreading that leaves the count unchanged still shows in the answer itself: a plan whose stays do not share their flight days, or that ends after the stated total. So the check is aimed at exactly the failure the count misses. This test asks whether the gate as it stands (count, then check) carries to a second domain. It is not a new variant chosen on test numbers: the checker, its token budget and the flag rule are PREREG_GC's.

**What a check can add at most.** Computed before this file from the stored runs (scratch script, no model call). A perfect check costing 1 ktok on every count-1 step, flagging exactly the wrong passes, gives checked − plain ladder utility of:

| Model | Perfect check − plain ladder |
|---|---|
| Qwen3-32B | +4.1 [+1.9, +6.6] |
| Qwen3-8B | +4.1 [+1.8, +6.9] |
| gpt-oss-20b | +6.7 [+4.1, +9.7] |
| gpt-oss-120b | +2.2 [+0.5, +4.2] |

At 2 ktok per check, the four values are +3.8, +3.9, +6.2 and +1.8. A real check flags fewer wrong plans and some right ones, so its gain is smaller.

**Setup.**
- **Check (`run_plan.py --check <tag>`).** For every count-1 row of the test runs (`trc`, `trct`, seeds 1–3), the same model as translator gets one call:
  - thinking on, 8,000 tokens, temperature 0.7;
  - seed = run seed × 10007 + trip number + 99;
  - prompt: the task without NaturalPlan's examples (its 0-shot text), the day-convention sentence of addendum NP-DAY, and the plan, one line per stay.
  - It is asked to check the plan against each requirement the task states, in turn, and to end with JSON `{"violated": [...]}`.
  - A non-empty list is a flag. An unparsed answer is no flag, as in PREREG_GC.
  - The plan shown is the stored plan of the row; no program is re-run.
- **Checked ladder.**
  - As PREREG_NP's ladder, but a count-1 step whose plan is flagged goes on to the next step (`trc` → `trct` → `think`).
  - The check's tokens are paid on every count-1 step the ladder reaches.
- **Read with** `python3 poc/gp_eval.py --np <tag> --check checkt`. Utility = 100·right − 0.5·ktok, bootstrap over trips (each trip's mean over seeds), 95%.
- **Models:** Qwen3-32B-AWQ (decides), Qwen3-8B, gpt-oss-20b, gpt-oss-120b (reported).
  - Each model checks its own translations: same server, same rows as PREREG_NP.
  - gpt-oss checks at high reasoning effort.
- **Dev, for format only:** the count-1 rows of the dev pilots (`q8b3`, `oss20`, 30 dev trips). They are checked first, and the check is read for parse failures and truncation only, not for accuracy. If more than 10% of dev checks are unparsed or truncated, the prompt's format line (not its content) may change once, recorded here before the test checks run.

**Predictions (Qwen3-32B decides; the other three are reported with the same lines).**
- **NPC-P1 (gate validity):** unflagged count-1 precision on the checked ladder, pooling `trc` and `trct` passes, at least 95%.
- **NPC-P2:** checked ladder − plain ladder, utility interval above 0.
- **NPC-P3:** checked ladder − think, utility interval above 0.

**Decision.**
- **NPC-P1 holds:** the gate with its check is valid on trips, and trips join grids as a second domain for the full method (count, then check, then escalate), with NPC-P3 as its result against thinking.
- **NPC-P1 fails:** the checker shares the translator's misreading on trips as well (Semantic Self-Verification's stated gap, as for the thinking translation on GridPuzzle). Trips then stay a negative result for the gate, as PREREG_NP's rule reads.
- **NPC-P2** is reported either way. It says whether the check pays for itself on trips; its ceiling is the table above.

**Dev format pilot, read 2026-11-10 21:1x UTC.** The dev pilots hold only two count-1 rows (`q8b3` 1, `oss20` 1): both checks parsed, neither truncated (0.98 and 1.95 ktok). The format line is unchanged. The test checks started on all four models.

**Correction to the dev note above (written 2026-11-10 22:1x UTC).** The dev note was wrong. I read the dev check files while the lanes were still writing them, so I saw one row each; the finished dev files hold 17 (`q8b3`) and 34 (`oss20`) checks. Read now: `q8b3` 0 unparsed, 0 truncated; `oss20` 5 of 34 truncated at 8,000 tokens and so unparsed (15%), above the 10% bar that would have allowed one format change. The test checks had already started, so no change was made and the registered setup ran as written. This affects only gpt-oss-20b, a reported row: 69 of its 301 test checks are truncated and read as no flag, as registered.

## Result, read 2026-11-10 22:1x UTC (`python3 poc/gp_eval.py --np <tag> --check checkt`)

| Model | Wrong plans flagged | Right plans flagged | ktok per check | NPC-P1 unflagged precision (≥ 95) | NPC-P2 checked − plain ladder | NPC-P3 checked ladder − think | Ceiling (perfect check) |
|---|---|---|---|---|---|---|---|
| **Qwen3-32B (decides)** | 18/18 | **115/196** | 1.71 | **74/75 = 98.7% ✓** | **−14.7 [−20.7, −8.8] ✗** | **+0.7 [−2.8, +4.4] ✗** | +3.9 [+1.7, +6.4] |
| Qwen3-8B | 29/30 | 22/123 | 2.60 | 96/97 = 99.0% ✓ | −0.2 [−3.8, +3.2] | +6.6 [+1.8, +11.6] | +3.7 |
| gpt-oss-20b | 12/27 | 1/274 | 5.57 (69 truncated) | 208/224 = 92.9% ✗ | +1.3 [−0.4, +3.2] | +0.2 [−5.1, +5.8] | +4.8 |
| gpt-oss-120b | 9/16 | 18/405 | 2.94 | 239/245 = 97.6% ✓ | −0.6 [−2.0, +0.9] | +5.1 [+0.8, +10.0] | +1.4 |

(One Qwen3-32B and one gpt-oss-20b count-1 step have an empty plan and no check row; they count as unflagged, so wrong.)

**Decision, by the rule as written.** NPC-P1 holds for Qwen3-32B. So, read literally, the gate with its check is valid on trips. **But it holds only because the checker flags 59% of right plans:** a check that flags almost everything is precise on what it leaves. The criterion I registered measures precision without coverage, and that is a flaw in the registration. The rule's own follow-on reading settles it: NPC-P3 (against thinking) is a tie, and the checked ladder loses 14.7 points of utility to the plain ladder. **So the check does not carry to trips as a working part of the method.** The plain ladder's win (PREREG_NP, +15.4) stands, without a valid gate.

**Why the 32B checker flags right plans (texts read).** It misapplies the same day convention the translators misread, in the other direction:
- It counts a stay of days 9–13 as 4 days instead of 5.
- It adds the stays' lengths as the total, ignoring the shared flight days ("22 days instead of 21").

The convention sentence is in its prompt. On trips, the convention is the domain's one hard reading, and both the translator and the checker get it wrong. A checker from the same model does not read it independently.

## Addendum NPC-X, written 2026-11-10 22:2x UTC, before any cross-family check has run: does the check fail because the checker shares the reading?

**Why.** The result above has a mechanism claim in it: the same-model check fails on trips because the translator and the checker share the domain's one hard reading, the day convention. If that is the cause, a checker from another model family that reads the convention right should flag few right plans. gpt-oss-120b's own checks flagged only 18 of its 405 right plans. If the over-flagging comes from checking day ranges as such, it should persist. Prior work on checkers from another family:
- VERGE (2601.20055): disagreement from another model family detects 94% of unfaithful unanimous formalizations, at 29% precision.
- Ours: XPEER, a peer's quick answer as the check on MAMO; idea 30, gpt-oss-20b checking Qwen3-8B's grids (it catches more wrong grids, flags 3 of 38 right ones).

**Setup.**
- gpt-oss-120b (high effort) checks Qwen3-32B's 214 count-1 plans, with the same prompt, budget and seeds as PREREG_NPC (`run_plan.py --check q32 --label checkt_oss120`).
- Read with `gp_eval.py --np q32 --check checkt_oss120`. Tokens are priced the same for both models (0.5 per ktok), so cost is counted, not price.

**Predictions.**
- **X1:** right plans flagged at most 10 of 196, against 115 for the same-model check.
- **X2:** wrong plans flagged at least 9 of 18.
- **X3** (reported): checked − plain ladder utility. The ceiling is +3.9 [+1.7, +6.4].

**Decision.**
- **X1 and X2 hold:** the same-model check failed because the reading is shared. On a domain with such a trap, the check must come from another family. That is a claim about when a free check works, and it goes to the report with the trips result.
- **X1 fails:** checking day ranges is hard for strong models as well. Trips stay closed for checks.

### NPC-X result, read 2026-11-10 22:3x UTC (`gp_eval.py --np q32 --check checkt_oss120`)

- **X1 holds:** gpt-oss-120b flags 6 of 196 right plans (same-model check: 115).
- **X2 holds:** it flags 17 of 18 wrong plans.
- **X3:** checked − plain ladder +2.5 [+0.1, +5.1] utility, 71% of the perfect-check ceiling (+3.5 on the same rows).
- Unflagged precision is 177/179 = 98.9%, now with coverage kept. Checked ladder 72.0% at 21.2 ktok, against thinking 47.0%: **+17.9 [+11.9, +24.1] utility**.

**Decision, as registered:** the same-model check failed because the reading is shared. On trips, a check from another model family makes the gate precise and pays.

**Origin, stated plainly:** this addendum was written after the same-model result, on the same rows, so it is one pair of models on one test set. The 2×2 addendum below separates the checker's family from its strength.

## Addendum NPC-X2, written 2026-11-10 22:3x UTC, before these runs: family or strength?

In NPC-X the checker differed from the translator in two ways. It was from another family, and it was a model that reads the convention right on its own plans. The two must be separated before the claim "the check must come from another family" is written.

**Runs (same prompt, budget and seeds):**
1. Qwen3-32B checks gpt-oss-120b's 421 plans: another family, and a checker that misreads the convention.
2. gpt-oss-120b checks Qwen3-8B's 153 plans: another family, strong checker.
3. gpt-oss-20b checks Qwen3-32B's 214 plans: another family, weaker, high effort. Reported only, because 23% of its own checks were cut off at 8,000 tokens.

**Predictions:**
- **X2-1:** run 1 flags more than 25% of gpt-oss-120b's right plans. This would mean the checker's own misreading drives false flags, whoever wrote the plan.
- **X2-2:** run 2 flags at most 5% of Qwen3-8B's right plans and at least 50% of its wrong ones.

**Decision.**
- **Both hold:** the claim is "a free check works when the checker reads the domain's hard reading right and does not share the translator's errors". A different family is the means, not the condition.
- **X2-1 fails** (the 32B checker does not over-flag another model's right plans): its false flags depend on the plans it sees. That would point at shared-plan effects, read in the texts.

### NPC-X2 result, read 2026-11-10 22:4x UTC

| Checker → plans of | Wrong flagged | Right flagged | Unflagged precision | Checked − plain ladder | Checked ladder − think |
|---|---|---|---|---|---|
| Qwen3-32B → gpt-oss-120b | 12/16 | **239/405 (59%)** | 97.4% | −9.8 [−14.2, −5.9] | −4.1 [−6.9, −0.8] |
| gpt-oss-120b → Qwen3-8B | 30/30 | **7/123 (5.7%)** | 100% | +1.5 [−1.6, +4.7] | +8.4 [+3.3, +13.6] |
| gpt-oss-20b → Qwen3-32B (reported) | 6/18 | 2/196 | 93.1% | −1.2 [−2.8, +0.4] | +14.1 [+7.8, +20.6] |

(gpt-oss-20b: 44 of 214 checks cut off at 8,000 tokens and read as no flag.)

- **X2-1 holds:** the 32B checker flags 59% of gpt-oss-120b's right plans, the same rate as on its own plans (115/196). Its false flags come from its own misreading of the day convention, whoever wrote the plan. A checker from another family is not enough.
- **X2-2 fails narrowly:** gpt-oss-120b flags 7 of 123 right Qwen3-8B plans (5.7%, against a bar of 5%), and all 30 wrong ones.
- So the registered "both hold" decision is not reached. The reading the data support:
  - The checker's own reading of the domain's hard part decides how often it flags right plans (59% for the 32B checker on either model's plans; 1–6% for gpt-oss-120b on any model's).
  - Independence decides how many wrong plans it catches: gpt-oss-120b catches 17/18 and 30/30 of other models' wrong plans, but only 9/16 of its own.
  - A useful free check needs both: a checker that reads the trap right and does not share the translator's errors.

### Addendum NPC-T, registered 2026-11-10 23:5x UTC, before any of its runs: is a miss decided by the error's type or by who wrote the plan?

**Why.** The NPC-X2 reading above says a checker catches other models' errors but not its own ("independence"). Reading the 16 wrong plans of gpt-oss-120b that its own check sees, by the way each plan breaks the task (`poc/np_uniq.py error_types`, applied to every stored wrong count-1 plan; `poc/gp_eval.py --np <tag> --check <label>` prints the split), points elsewhere:
- 5 of the 16 break the task in one way only: a dated event ("meet a friend in Naples between day 18 and day 20") overlaps the stay but is not inside it. This is right under the "overlap" reading of the window and wrong under the task's ("inside", the reading under which 95 of the 100 trips have one plan). The gpt-oss-120b checker flags 0 of these 5, the Qwen3-32B checker 1 of 5, and gpt-oss-20b flags 1 of its own 7.
- On every other wrong plan, gpt-oss-120b flags 9 of its own 11, and 47 of 48 of the Qwen models'.
- Qwen3-8B's and Qwen3-32B's wrong passes contain no plan of the overlap-only type. So "it misses its own errors" may only mean "its own errors include a type that no checker reads as an error".
- Example, trip 1392: gpt-oss-120b's program reads the Naples window as an overlap and, after a count of 2, adds a requirement the task does not state ("in Split on some day 14–18"), which pins one plan. The checker reads the plan against the text; it sees the window the same way and passes it.

**Two explanations, two predictions.**
- **Type:** whether a checker flags a wrong plan depends on the kind of break and the checker's own reading of it, not on who wrote the plan; the window reading is shared by all four models.
- **Identity:** a checker misses errors of its own model (or family); a checker from the other family catches the overlap-only plans.

**Runs** (PREREG_NPC's prompt, thinking, 8,000 tokens, temperature 0.7, the same seeds; labels `checkt_<checker>`):
1. Qwen3-8B checks gpt-oss-120b's 421 plans and gpt-oss-20b's 301 (other family; 12 overlap-only wrong plans).
2. Qwen3-32B checks gpt-oss-20b's 301 plans (other family; 7 overlap-only).
3. gpt-oss-120b checks gpt-oss-20b's 301 plans (same family; 7 overlap-only, 20 other).
4. Qwen3-32B checks Qwen3-8B's 153 plans, and Qwen3-8B checks Qwen3-32B's 214 (false flags only).

**Predictions** (counts of flags; unparsed reads as no flag, as registered):
- **T1 (type):** each of Qwen3-8B (run 1, 12 plans) and Qwen3-32B (run 2 with its 1/5 above, 12 plans) flags at most 3 of 12 overlap-only wrong plans, and gpt-oss-120b (run 3) at most 2 of 7.
- **T2 (type):** gpt-oss-120b flags at least 16 of gpt-oss-20b's 20 other wrong plans, as it does other models' (47/48), although they share a family.
- **T3 (false flags are the checker's):** the share of right plans flagged lies, for Qwen3-8B, in [10%, 30%] on each of gpt-oss-120b's, gpt-oss-20b's and Qwen3-32B's plans (own: 22/123 = 18%); for Qwen3-32B, in [45%, 70%] on gpt-oss-20b's and Qwen3-8B's (own 59%, gpt-oss-120b's 59%); for gpt-oss-120b, at most 8% on gpt-oss-20b's (1–6% so far).

**Decision.**
- **T1 and T2 hold:** the claim in FINDINGS changes from "catches follow independence from the translator" to "a check catches the breaks the checker reads as breaks; a reading every model shares (here the event window) is invisible to any of them, whoever wrote the plan". The paper's condition for a useful free check then reads: the checker must read each requirement the way the task does, and translator identity matters only through which kinds of break it makes.
- **A Qwen checker flags at least 6 of 12 overlap-only plans:** the window reading differs by family, and the identity reading of NPC-X2 stands for this break.
- **T2 fails** (gpt-oss-120b flags fewer than 16 of 20): sharing a family hides errors beyond the window reading; read the missed plans.
- T3 is read on its own: a miss means false flags depend on the plans seen, not only on the checker.

### NPC-T result, read 2026-11-11 00:5x UTC

All six runs finished; unparsed checks 0–5 per run. Rows: who checks whose plans. "Overlap only" = wrong plans whose one break is an event window that overlaps the stay without lying inside it.

| Checker → plans of | Right plans flagged | Wrong, overlap only, flagged | Wrong, other, flagged | Checked − plain ladder, utility |
|---|---|---|---|---|
| Qwen3-8B → gpt-oss-120b | 76/405 (18.8%) | 1/5 | 8/11 | −3.3 [−5.8, −1.2] |
| Qwen3-8B → gpt-oss-20b | 61/274 (22.3%) | 2/7 | 19/20 | +0.7 [−2.5, +4.0] |
| Qwen3-8B → Qwen3-32B | 39/196 (19.9%) | – | 15/18 | −3.1 [−6.7, +0.4] |
| Qwen3-32B → gpt-oss-20b | 159/274 (58.0%) | 4/7 | 19/20 | −7.0 [−11.6, −2.4] |
| Qwen3-32B → Qwen3-8B | 74/123 (60.2%) | – | 30/30 | −10.3 [−15.3, −5.3] |
| gpt-oss-120b → gpt-oss-20b | 6/274 (2.2%) | 2/7 | 19/20 | **+3.9 [+1.3, +6.7]** |

**Predictions.**
- **T1 fails as registered for Qwen3-32B:** with its 1/5 on gpt-oss-120b's plans it flags 5 of 12 overlap-only plans (bar: at most 3). It holds for Qwen3-8B (3 of 12) and gpt-oss-120b (2 of 7).
- **T2 holds:** gpt-oss-120b flags 19 of gpt-oss-20b's 20 other wrong plans, as it does other models' (47/48), although the two share a family.
- **T3 holds in all six cells:** Qwen3-8B flags 18.8–22.3% of right plans on three other translators (own 18%); Qwen3-32B 58–60% (own 59%, gpt-oss-120b's 59%); gpt-oss-120b 2.2% (1.5–5.7% elsewhere).
- **The identity branch is not reached:** no Qwen checker flags 6 or more of the 12 overlap-only plans.

**Decision.** T1 is not met, so the registered "T1 and T2 hold" change is not made in full. What the data do support:
1. **False flags are the checker's, not the plan's.** Across four translators each, each checker's right-plan flag rate stays within 4 points of its own rate (T3). This is the strongest result of the three checks on trips.
2. **The identity reading of NPC-X2 is withdrawn.** gpt-oss-120b catches 19/20 of its own family's other errors (T2). Its earlier misses on its own plans are window breaks. No Qwen checker reaches the identity bar on those breaks.
3. **The window break is mostly unseen:** 9 of 31 checks of overlap-only plans flag them.
   - Qwen3-32B's 5 of 12 flags are at the rate it flags right plans of the same translator (58%), so they do not show it reading the window.
   - Read after the result, so reported only: 2 of its 5 flags name the broken event. The other three cite the trip's length or a stay, or list every requirement.
4. **One checker is best for every translator.** gpt-oss-120b, the checker with the fewest false flags, gives the largest checked-ladder gain over the plain ladder on all three other translators: +2.5, +1.5 and +3.9 for Qwen3-32B, Qwen3-8B and gpt-oss-20b. On its own plans it gives −0.6.

**For idea 43.** False flags are a stable property of a checker, and they decide most of a check's value here. So a checker could be chosen by measuring its false-flag rate once, on any one translator's plans, and carrying it to the others. That measurement still needs labels. A label-free version would need the flag rate, which mixes false flags with catches. That is the next question.
