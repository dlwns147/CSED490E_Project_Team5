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
