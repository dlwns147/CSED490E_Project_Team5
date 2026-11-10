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
