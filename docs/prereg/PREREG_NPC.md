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
