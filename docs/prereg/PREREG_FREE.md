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

## Addendum FREE-MIN: a free check from how the puzzle was made, registered 2026-11-11 10:1x UTC, before any program is re-run for it

**Why.** On ZebraLogic, 20 of 25 wrong count-1 programs misread one template phrase and still have a unique solution, so neither the count nor the text checks see them (FREE-ZL). One more property of the puzzle is free. ZebraLogic's generator removes clues, one at a time, until no clue can go without a second solution appearing (Lin et al. 2502.01100, section on generation). So in a faithful translation every clue is needed: dropping any one leaves at least two solutions. A misread clue changes the constraint, and the other clues were not chosen to be minimal for it, so some clue may become unneeded. The check uses only the solver, and no list of phrases.

**Check (`poc/gp_rescore.py --zlmin`, in the container).** Each stored count-1 program is re-run once per clue, with that clue dropped. The program is flagged if some clue can be dropped with the solution staying unique.

**Data.** ZL-AM (`q8bam`, `oss20am`; arms tr and trt) and the main ZebraLogic runs of Qwen3-8B (`q8bh`, `q8bf`; arms trf and trt). Three seeds each; scoring v2 for right and wrong.

**Predictions.**
- **FREE-MIN-P1.** Right count-1 programs: at most 10% flagged, per tag. A faithful translation that splits one clue into two expressions can leave one of them unneeded, which is why this is not 0%.
- **FREE-MIN-P2.** Qwen3-8B's 25 wrong ZL-AM programs: at least half flagged.

**Decision.** Both hold: the necessity check joins the free checks for generators that minimise their clues, and a fresh-run test of it as feedback is registered next. P1 fails: the check is too strict for translations as written. P2 fails: misreadings keep every clue needed, and the reading gap stays open.

## Result FREE-MIN (2026-11-11 18:1x UTC): FREE-MIN-P1 holds, FREE-MIN-P2 fails
Job 1384271 (`poc/gp_rescore.py --zlmin`), read with `python poc/gp_eval.py --zlmin`. A program is flagged when some clue can be dropped with the solution staying unique.

| Tag | Right count-1 flagged (P1: ≤ 10%) | Wrong count-1 flagged |
|---|---|---|
| q8bam (ZL-AM, Qwen3-8B) | 3/455 (0.7%) | **6/26 (23%)** (P2: ≥ half) |
| oss20am (ZL-AM, gpt-oss-20b) | 0/593 (0.0%) | 0/2 |
| q8bh (main, Qwen3-8B, unseen puzzles) | 16/1687 (0.9%) | 31/60 (52%) |
| q8bf (main, Qwen3-8B, dev) | 25/2532 (1.0%) | 12/35 (34%) |

- Every program re-ran to count 1 with all clues, and every clue list was read.
- The stored q8bam set has 26 wrong count-1 programs (21 quick, 5 thinking), one more than the 25 written in the registration; scoring v2 is not stored for q8bam, so the stored `exact` is used.
- **FREE-MIN-P1 holds.** Right programs are flagged in at most 1.0% of cases per tag.
- **FREE-MIN-P2 fails.** 23% of the Qwen3-8B ZL-AM wrong programs are flagged, below half.
- **Decision (as registered):** misreadings mostly keep every clue needed, and the reading gap stays open. On the main puzzles the flag catches half of the wrong programs (52%) at a 0.9% false-flag rate; that set was not registered, so this is descriptive.
- Flags are uneven by puzzle: they cluster on some sizes (for q8bh, 5×2 6/6 and 6×4 4/4, but 2×6 0/7 and 6×5 0/6). Whether a misread clue leaves another clue unneeded depends on the puzzle, not on the misreading.

## Interim (2026-11-11 20:3x UTC): FREE-P3 and FREE-P4 hold for Qwen3-32B-AWQ and gpt-oss-20b; P1 and P2 wait on the Qwen3-8B rerun
`python poc/gp_eval.py --free <tag> --score2`, fresh seeds 4–6, all 645 GridPuzzle and 282 Mitra-Baral puzzle-seeds.

| Translator, set | v-ladder − plain ladder (P3: point ≥ −0.5) | v-ladder − think | Accepted count-1 precision (P4: ≥ 98%) |
|---|---|---|---|
| Qwen3-32B-AWQ, GridPuzzle | +0.3 [−0.3, +1.0] | +10.6 [+6.9, +14.5] | 461/468 = 98.5% |
| Qwen3-32B-AWQ, Mitra-Baral | +0.5 [−0.2, +1.6] | +1.3 [−1.3, +3.9] | 252/257 = 98.1% |
| gpt-oss-20b, GridPuzzle | +1.3 [+0.0, +2.8] | +4.8 [+1.5, +8.2] | 473/480 = 98.5% |
| gpt-oss-20b, Mitra-Baral | +1.5 [+0.2, +3.3] | +2.0 [+0.1, +4.1] | 268/269 = 99.6% |

- **Qwen3-8B rerun.** Its runs (Slurm job 1379922, one A5000) had finished about 30 of 215 puzzles per run after 7 hours. The 24 GB card held 10 requests at a time, with 374 waiting. I cancelled the job, dropped those partial rows, and restarted all 12 runs from the first puzzle on two 96 GB GPUs of the second server, with every setting unchanged.
