# PREREG_ADJ — escalate with the evidence: the thinking call sees the two disagreeing programs (registered 2026-11-22 06:5x UTC, before any row)

**Why.** After PREREG_ESCT, the largest remaining error on held-out word problems is thinking that prints a wrong value on an escalated
problem (Qwen3-8B 385 of 3,384 non-routed problem-seeds, gpt-oss-20b 477 of 3,434). The escalation discards the evidence that caused it:
two programs (the model's own after the repair turn, and the cross-family peer's) that disagree. First test (poc/analyze_sol2.py, stored
rows): on those wrong rows, one of the two programs is right on 31% / 24% (raw) and 34% / 27% (audited). The thinker could recover at
most these; it may also lose rows it now gets right.

**Prior work.** Mixture-of-Agents aggregation (Wang et al. 2024), Universal Self-Consistency (Chen et al. 2023), multi-agent debate
(Du et al. 2023), Self-Debug (execution feedback, one model). This is a known mechanism (an aggregator over candidate solutions); what is
specific here is that the candidates come from two model families, are executed, and are shown only when they disagree inside a
cost-aware cascade. Loop mark: K (known mechanism), not M.

**Arms** (held-out pool: x3, OptMATH, OptiBench, BWOR, LogIOR; seeds 1–3; both models):
- ESCT: PREREG_ESCT's final method (typed → own → repair → peer → think → retry: Qwen3-8B hands off to gpt-oss-20b's think, gpt-oss-20b
  retries with its next seed's think).
- ADJ: the same, except the think on every escalated problem-seed is a new call `run_nlopt.py <m>_<set> thinkadj <seed>`: the stored
  think's prompt (x3: mip + snippet; other sets: free) followed by both programs with their printed values, in a seed-fixed order,
  and the instruction to compare them with the statement and write a correct program. Same call settings as the stored thinks (thinking
  on, 16k cap, temperature 0.7, default effort). The retry step is unchanged and uses the stored thinks.
- Cost: the adjudicating think's output tokens replace the stored think's (its longer input is reported in the in+out view only).

**Test.** Per model, utility at 0.5 per ktok (output tokens), ADJ − ESCT, one-sided bootstrap clustered by problem, Holm over the two
models (poc/analyze_adj.py). A model's test HOLDS if Holm p < 0.05 on raw labels AND on expert-audited labels (OR_CLEAN=1).
**Prediction:** small: ceiling +3.4 (Qwen3-8B) / +3.3 (gpt-oss-20b) points if every recoverable row were recovered and none lost;
expected +0.5 to +1.5. If neither holds, the escalation tier stays as in ESCT and the report states that adjudication does not pay.
