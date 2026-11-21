# PREREG_ESCT — what to do when the escalation's thinking program fails visibly (registered 2026-11-22 09:44 UTC)

**Why (M-B).** On the held-out pool most remaining errors are escalated problems whose thinking is wrong (Qwen3-8B 32 points, gpt-oss-20b
26). Reading the 754 / 590 such rows on audited labels (poc/analyze_esct.py --census): **66% of Qwen3-8B's and 47% of gpt-oss-20b's failed
thinks crash or print no value** — a visible failure that the reported method (PREREG_TYPED J) answers with nothing. The recipe's own
step for this ("a failed think gets one retry", PROJECT.md §2) was not in the measured method. On those failures the other family's
thinking is right on 38% of Qwen3-8B's rows and 18% of gpt-oss-20b's; the same model's own retry is unknown until scored.
Prior work: retry / self-repair after execution failure (Self-Debug; our HO-CC retry), cross-family second opinion (our XPEER); new is
choosing the retry's model by the evidence that the first family failed visibly.

**Arms (offline on stored rows; no arm below has been scored; per-row census seen above).** Base = J's full method.
- J+RS: on a visible thinking failure (crash, no value, 'No Best Solution'), the same model thinks again (its next seed's stored think).
- J+RX: on a visible thinking failure, the other family thinks (its stored think, same seed).
Tokens of the retry are paid; utility at rate 0.5; held-out pool (x3, OptMATH seed 1, OptiBench, BWOR, LogIOR); clustered by problem.
- **E-1** J+RX − J > 0 for Qwen3-8B. **E-2** J+RS − J > 0 for gpt-oss-20b. **E-3** (choice) J+RX − J+RS > 0 for Qwen3-8B and < 0 for
  gpt-oss-20b (a weaker main model should hand off to the stronger family; a stronger one should retry itself).
Holm over E-1, E-2 and the two E-3 directions; raw AND audited labels. Decision: the tests that hold on both label sets enter the method.

## Result (2026-11-22 09:46 UTC; python3 poc/analyze_esct.py, raw and OR_CLEAN=1; held-out pool 3,472 / 2,728 rows)
| test | raw | audited |
|---|---|---|
| E-1 Qwen3-8B J+RX − J | **+7.25 [+6.22, +8.35] holds** | **+7.05 [+5.87, +8.30] holds** |
| E-3 Qwen3-8B J+RX − J+RS | **+4.19 [+3.16, +5.28] holds** | **+4.03 [+2.83, +5.27] holds** |
| E-2 gpt-oss-20b J+RS − J | **+3.89 [+3.27, +4.56] holds** | **+3.69 [+3.02, +4.41] holds** |
| E-3 gpt-oss-20b J+RS − J+RX | **+1.82 [+1.22, +2.45] holds** | **+2.10 [+1.44, +2.80] holds** |
Accuracy / tokens (raw): Qwen3-8B 62.4% at 6.6k → 70.1% at 7.5k (RX); gpt-oss-20b 69.0% at 3.2k → 73.2% at 3.8k (RS).
**Decision (registered):** all four hold on both label sets. The method adds a last step: on a visibly failed think, Qwen3-8B hands
the problem to gpt-oss-20b's thinking; gpt-oss-20b retries its own. The weaker main model should hand off, the stronger should retry.
Descriptive, the new method − LLMOPT-14B per held-out set: Qwen3-8B raw +7.6 / +19.5 / +5.5 / +27.5 / +32.4 (x3, OptMATH, OptiBench,
BWOR, LogIOR), audited OptiBench +2.4 [−0.3, +5.1] (was −3.9 [−6.8, −1.1]); gpt-oss-20b ahead on every set with both label sets
(audited OptiBench +5.3 [+2.4, +8.2]). The OptiBench loss to the specialist came from failed thinks the method answered with nothing.
