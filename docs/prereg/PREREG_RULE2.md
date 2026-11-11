# PREREG_RULE2: stated rules carried over from a label-free pass on earlier puzzles, tested on fresh seeds, registered 2026-11-11 19:2x UTC, before any run

**Why.** PREREG_RULE (result 2026-11-11 19:2x UTC) found:
- The model's own stated rules fix its quick reading ("between" misread 11–15%).
- The ladder gains +3.5 [+1.3, +5.9] over the quick step without any fact.
- Against the hand-written fact it is −0.2 [−2.2, +2.0], missing the −2.0 margin by 0.2.
- The deficit is the cold start. trr − trf per puzzle is −4.0, −2.9 and +0.3 at positions 50–149, before the "between" rule is stated (positions 86–96), and +1.7, +2.0 and +1.7 at positions 150–249.

The fact is present from the first puzzle; the rules have to be learned. A deployed ladder has seen earlier puzzles of the same set, so the fair comparison starts from rules stated on earlier traffic. This file tests that on seeds no arm has used.

**The method (arm `trrw`: `poc/run_zebra.py --zl q8bh trr <seed> --skip 10 --warm q8bf:1`, as committed with this file).**
- First, `trr` exactly as in PREREG_RULE on the 250 dev puzzles (`q8bf`, seed 1), using the stored `zl_q8bf_trt_s1` rows as the ladder's thinking step.
  - These are the puzzles on which the fact was written. trr reads no label and no fact, only the solver's count, so nothing we learned from them enters.
- `trrw` starts each cell B run with that run's stated rules, in order, and keeps stating new ones as trr does. Everything else is as trr.
- The dev pass costs quick and thinking translations of earlier puzzles. That cost is reported but not charged to cell B, as the fact's writing is not charged to trf.

**Runs (Qwen3-8B, cell B = the 250 unseen main puzzles, `--skip 10`, fresh seeds 4, 5, 6).**
- `tr`, `trf`, `trt` (8,192 tokens a round), `think` (`--max_tokens 32000`) and `trrw`, with every setting as the stored seeds 1–3.
- Ladder: quick step → `trt` → `think`, every step paid; utility = 100·exact − 0.5·ktok; 95% bootstrap over puzzles, a puzzle's seeds together.
- `python poc/gp_eval.py --conv --rule2`.

**Predictions.**
- **RULE2-P1 (decides):** ladder(`trrw`) − ladder(`trf`): the lower bound is above −2.0 (as RULE-P4) and the point is at or above 0.
  - Derivation: without the cold start, positions 50–149 move from about −2.2 toward 0, and positions 150–249 keep about +1.8. The expected total is about +0.7 to +1.1.
  - The interval half-width at three seeds was about 2.1, so the expected lower bound is about −1.2.
- **RULE2-P2:** ladder(`trrw`) − ladder(`tr`): the interval is above 0. Expected about +4.5, the +3.5 of RULE plus the cold-start share.
- **RULE2-P3:** "between" clues misread in `trrw` programs, counted from the first puzzle: at most 30%.

**Decision.**
- **P1 and P2 hold:** the ZebraLogic headline is restated without the hand-written fact. The quick translation reads with rules it stated itself from count-admitted escalations, on earlier puzzles and as it goes. The fact becomes an ablation.
- **P1 fails:** the hand fact stays, disclosed as dev-mined. trr is reported as the label-free alternative that gains over no fact (RULE-P3).
- In both cases the seeds 1–3 cold-start result is reported alongside.

**Prior work.** As PREREG_RULE: HtT (2310.07064), TRAN (2310.15746), LEAP (2402.05403), Dynamic Cheatsheet (2504.07952). Carrying a rule library from a training pass to test is HtT's setting; ours builds the library without labels.

## Addendum (2026-11-11 20:3x UTC): the first run tested nothing new, because its dev pass read the wrong file. Rerun with the registered method; predictions unchanged.
- **What went wrong.** The command above names `q8bf` as the dev pass. The 250 dev puzzles (ids 0–9 of each size, where the fact was written) have their thinking translations under tag `q8b` (`zl_q8b_trt_s1`). `zl_q8bf_trt_s1` holds 500 other puzzles (ids 20–39). So the dev pass found no thinking row for any of its puzzles, stated no rule, and every `trrw` run started empty. Those runs are `trr` with a cold start on seeds 4–6, not the registered method.
- **Fix.** The dev pass is now `--zl q8b trr 1`, and `trrw` uses `--warm q8b:1`. `run_zebra.py` now stops when the thinking file lacks any of the puzzles.
- **The first runs are kept** as `zl_q8bh_trr_s{4,5,6}` (cold start, fresh seeds). They replicate PREREG_RULE on new seeds. I read them before the rerun, so I report them here, and they change no prediction.

| Fresh seeds 4–6, 707 of 750 puzzle-seeds (thinking still running on 43) | Utility difference |
|---|---|
| ladder(trr, cold) − ladder(tr) | +2.2 [+0.2, +4.4] |
| ladder(trr, cold) − ladder(trf) | −0.3 [−2.2, +1.5] |

- "Between" clues misread: tr 94%, trf 13%, trr (cold) 24%. Count-1 precision: trr 96.4%, trf 96.6%.
- The seeds 1–3 values were +3.5 and −0.2. So the cold start sits near the fact again, with its lower bound again at about −2.2.

## Result (2026-11-11 21:3x UTC): RULE2-P1 and P3 fail, P2 holds. The hand fact stays. The carried rules made the reading worse.
`python poc/gp_eval.py --conv --rule2`, all 750 puzzle-seeds, seeds 4–6.

| Fresh seeds 4–6 | Utility difference |
|---|---|
| ladder(trrw) − ladder(trf) (P1: lower bound > −2.0, point ≥ 0) | **−0.4 [−2.4, +1.8]**, fails |
| ladder(trrw) − ladder(tr) (P2: interval above 0) | +2.0 [+0.4, +3.7], holds |
| ladder(trr, cold) − ladder(trf) | −0.2 [−2.1, +1.7] |
| ladder(trr, cold) − ladder(tr) | +2.1 [+0.2, +4.2] |

- **RULE2-P3 fails.** "Between" clues misread from the first puzzle: trrw 119/214 = 56%. Cold trr 27%, trf 19%, tr 95%.
- **Decision (as registered):** the hand fact stays, disclosed as dev-mined. trr is reported as the label-free alternative that beats no fact.

**Root cause (read from the rows).**
- **The dev library holds an inverted rule.** Its first "between" rule (position 58) says "a difference of 1 indicates one house between them, and a difference of 2 indicates two houses between them".
  - The pair it came from was right: the quick translation wrote `== 1`, the thinking translation `== 2`, and the count admitted the second.
  - The rule writer restated that pair in its own wrong reading. Right "between" rules follow from position 117 on, so the library contradicts itself.
- **The errors follow the inverted rule.** In trrw, "one house between" was written as a distance of 1 in 67 of 149 clues (cold trr: 36 of 170), and "two houses between" as 2 in 40 of 52 (cold trr: 33 of 74).
- **The library is long and repetitive.** The dev pass kept 40 rules, only 14 of them distinct. The runs added 41–69 more, with 8–14 distinct each, so late puzzles saw 80–100 lines.
- **The misreading grows along the stream:**

| Positions | trrw misread | cold trr misread |
|---|---|---|
| 50–149 | 20/47 | 19/49 |
| 150–199 | 39/71 | 15/80 |
| 200–249 | 60/96 | 35/109 |

- The inverted rule and the list's length can each explain this. A diagnostic (`poc/rule_diag.py`, not registered) re-translates the same puzzles with the same lists: with and without the inverted rule, and with each rule text kept only once.
- **Diagnostic result (21:4x UTC).** First-round misreads with the list as shown: 70%. Without the inverted rule: 43%. With each rule kept once: 67%. With both changes: 59%.
  - The inverted rule is the main cause; length is not.
  - The fix, a check that a stated rule reproduces the admitted reading, is registered as PREREG_RULE3.
