# PREREG_FREE: free text checks on top of the count, registered 2026-11-11 06:4x UTC, before any replay or fresh run is read

**Why.** The count accepts a translation whose clues allow exactly one grid. Reading the wrong grids that every checker passes (FINDINGS 2026-11-11 03:3x) gave three causes, and none is caught by the count or by a thinking check:
- **Misspelled values.** The program writes "Vuria Mari" for the listed "Viria Mari" and solves its own puzzle (12 of the 34).
- **Conclusions written as clues.** The translator solves part of the puzzle while translating and writes a conclusion in place of the clue ("Violet's pet is the boxer" written as "Violet goes with month 3"), or a repair adds a clue the text does not give in order to force one solution (11 of the 17 real errors).
- **"Either A or B" read inclusively.** The solution puts A and B in the same row, which only the inclusive reading allows (the rest of the 17).

All three can be checked against the puzzle's own text with no model call. The puzzle lists every value, each clue names the values it is about, and a clue's two alternatives can be checked on the solution. These checks are the method change. They follow from the causes above, not from a search over rules.

**Prior work.** Logic-LM (2305.12295) and SatLM (2305.09656) repair on solver errors only. LINC (2310.15164) votes over translations. The exact-cover zebra paper (ICLR 2026 workshop) refines by uniqueness. None checks the translation against the text it came from without a model.

**The checks** (`poc/grid_score.py: free_checks`, as committed with this file; the program is parsed, never run):
- **LV (listed values).**
  - Every value in `groups` names exactly one listed value of its category (`match`), and no two values of a category name the same one.
  - Every value a clue expression refers to names some listed value.
- **EA (entity alignment).** The translation prompt asks for one expression per clue, in order. When the counts agree, expression i must refer to every listed value outside the first category that clue i names (bare numbers excluded: "2" may be an offset). It does not apply otherwise.
- **OR (both readings).** For a clue "X is either A or B", where A and B each name one listed value and are of different categories, the solution must not put A and B in one row.

**Dev reading (before this file; design and parser fixes only).** Count-1 programs of the dev split, flagged right / flagged wrong:
- Qwen3-32B-AWQ: GridPuzzle 9 / 112 right and 4 / 5 wrong; Mitra-Baral 3 / 145 and 2 / 3.
- gpt-oss-20b: 0 / 27 and 1 / 38 right (no wrong ones).

The parser fixes were quoted values ("perle d'or"), values written as listed ("7:30am") and bare numbers. Every flagged right program read on dev wrote a conclusion in place of its clue ("Henrietta's design was silver" as "Henrietta == 35"; "the horned tortoise" as its age). Those flags are correct about the translation, even though the guess was right.

**Seen test cases (not evidence).** Of the 34 shared misses already read, the checks flag 27, including every misspelled-value case. That is a check of the implementation, since these errors shaped the checks.

**Test 1, replay (reported; informed by the read misses).** On the stored ladders (seeds 1–3), a flagged count-1 program is not accepted and the ladder moves to its next step (no repair). Grids for the OR check come from re-running the stored programs in the container (`gp_rescore.py`, which now keeps the grid). Command: `python poc/gp_eval.py --free <tag> --score2`.

**Test 2, fresh runs (decisive).**
- Arms `gtrv` / `gtrtv`: `gtr` / `gtrt` whose count-1 program must also pass the checks. A flagged program gets the flags back as feedback within the same 3 rounds ("...they do not say what the puzzle says: <flags>. Write each clue as the puzzle states it, not a conclusion drawn from several clues, with each value exactly as listed...").
- A program still flagged after the last round is not accepted.
- Seeds 4, 5, 6 on the GridPuzzle (215) and Mitra-Baral (94) test sets. Translators `q8b`, `q32a`, `oss20` (effort low / high).
- A v-run is identical to a plain run until its first flagged count-1 round. So the plain ladder on the same runs is read from the same rows: it accepts the first count-1 round. Paired exactly.
- Thinking: the stored think of seed k − 3.
- Command: `python poc/gp_eval.py --free <tag> --score2`.

**Derivation of the predictions.**
- Qwen3-8B accepts a wrong count-1 program on about 9.5% of GridPuzzle puzzle-seeds (61 of 645) and 5.7% of Mitra-Baral's.
- The thinking check of PREREG_GC caught 34 of the 61 and gained +2.0 [+0.3, +4.0] after paying for itself. That is about 53 utility points per caught puzzle-seed, so a caught wrong program is fixed about 60% of the time.
- With dev's catch rate (about 80%), the free checks would catch about 49. That gives about +4.0 on GridPuzzle, and they cost nothing on passes. A false flag (about 8% of right programs on dev) costs a repair round (about 1 point) and sometimes breaks the program: about −0.8 in all.
- Net about +3 on GridPuzzle for Qwen3-8B. For the precise translators (Qwen3-32B-AWQ, gpt-oss-20b, about 2.4% wrong) it is about +1, within noise.

**Predictions** (utility; paired by puzzle; 10,000-draw puzzle bootstrap):
- **FREE-P1.** Qwen3-8B, GridPuzzle: v-ladder − plain ladder on the same runs, interval above 0.
- **FREE-P2.** Qwen3-8B, GridPuzzle: v-ladder − think, interval above 0. This would restore the GP-P1 win that scoring v2 turned into a tie.
- **FREE-P3.** Qwen3-32B-AWQ and gpt-oss-20b, both sets: v-ladder − plain ladder point estimate at or above −0.5. The checks must not cost where translations are already precise.
- **FREE-P4.** Accepted count-1 precision of the v-ladder at least 98% for every translator and set.
- **Mitra-Baral for Qwen3-8B:** reported, with no prediction.

**Decision.**
- P1, P3 and P4 hold: the free checks become part of the method, stated as checking the translation against its source text at no model cost.
- P1 fails: the checks are reported as a diagnostic only.
- P3 fails: the checks are stated as paying only for imprecise translators.

## Addendum FREE-ZL: the same checks on ZebraLogic, registered 2026-11-11 10:1x UTC, before they are run there

**Why.** The checks were designed on grid puzzles (Puzzle Baron). ZebraLogic is a different generator with numbered clues and listed values too, so it tests whether they carry to a domain they were not shaped on. Amonkar et al.'s 100 puzzles (ZL-AM) have stored first-step translations (`tr`, no thinking, no template fact): count-1 precision 176 of 197 for Qwen3-8B and 296 of 298 for gpt-oss-20b.
- **Seen before this file:** 3 of Qwen3-8B's 21 wrong count-1 programs. One writes a conclusion in place of a clue (Eric's September birthday as "September is house 2"). Two read "there is one house between" or "two houses between" as a distance of 1 or 2, not 2 or 3, which no text check can see.

**Setup.** `grid_score.free_checks` unchanged. A ZebraLogic puzzle is given to it with the houses as the first category and each attribute's listed values from the puzzle's header (the gold rows' values, as `gp_rescore.py --zl` does). Count-1 programs of `tr` and `trt`, three seeds, both translators. OR does not apply (ZebraLogic's clues say "either" rarely).

**Predictions.**
- **FREE-ZL-P1.** Qwen3-8B: the checks flag at least a third of the wrong count-1 programs. The distance misreading is invisible to them, and it is at least a third of the errors.
- **FREE-ZL-P2.** False flags at most 5% of right count-1 programs, for each translator.

**Decision.** Both hold: the checks are stated as carrying to a second puzzle generator. P2 fails: their false-flag rate is generator-specific, and the parser is reported as the limit.

### FREE-ZL result (2026-11-11 10:1x UTC): P1 fails, P2 holds
- **P1 fails:** the checks flag 4 of Qwen3-8B's 25 wrong count-1 programs (16%; tr and trt, three seeds). gpt-oss-20b: 1 of 2.
- **P2 holds:** false flags 10 of 456 right programs (2.2%) for Qwen3-8B and 1 of 593 (0.2%) for gpt-oss-20b.
- **Why P1 fails:** 20 of the 25 wrong programs misread "there is one house between A and B" (or two) as a distance of 1 (or 2), one less than meant. That is far more than the third I assumed. The checks see none of these by design: the program names the right values and keeps one expression per clue. Of the other 5, they flag 3, each a conclusion written in place of a clue.
- **Decision as registered:** the checks are not stated as carrying to ZebraLogic. Their false-flag rate is low there too, so they cost little, but the dominant error on this generator is a reading of one template phrase.
