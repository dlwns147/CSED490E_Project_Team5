# Documents

| File | What it is |
|---|---|
| `FINDINGS.md` | Chronological lab log: one dated entry per result, decision or incident (newest at the end). |
| `prereg/PREREG_<id>.md` | One file per experiment: question, predictions written before the run, then the dated results and verdicts. |
| `notes/CRITIQUE.md` | Self-review of the project's weak points and how each was addressed. |
| `notes/CHECKS.md` | Which label-free check (statement examples, symmetry, feasibility, ...) covers which failure. |
| `notes/FIX_MAP.md` | The failure → cheapest-fix map that the project builds. |
| `notes/RELATED_WORK.md` | Prior work checked for each idea, with what is new here. |
| `notes/PROPOSAL_CORE_DRAFT.md` | Draft reframing of the proposal around "when can a model catch its own mistakes". |
| `notes/E1_TAXONOMY_DRAFT.md` | The failure taxonomy (classes and rules) used by `poc/analyze_e1_taxonomy.py`. |
| `archive/` | Earlier versions of `PROPOSAL.md` / `PROPOSAL_ko.md` from before the repository existed. |

The proposal itself (`PROPOSAL.md`, `PROPOSAL_ko.md`, `PROPOSAL_slides.pptx`) and the server notes (`HANDOFF.md`) are in the
repository root. Each experiment's exact commands are in `poc/queues/queue_*<id>*.sh` and its analysis in `poc/analyze_<id>.py`.

## Experiments by theme

Several files hold follow-up experiments after the first one (listed in the last column).

| Theme | File | Question | Also contains |
|---|---|---|---|
| Mechanisms on generated tasks | `PREREG_E2.md` | Do the helper-steering / hidden-contract mechanisms predict new tasks? | |
| | `PREREG_E4.md` | Does helper similarity to the needed algorithm drive steering? | |
| | `PREREG_L1.md` | Does steering survive when helpers are an importable library? | |
| Methods for helper context | `PREREG_M1.md` | A steering-score filter for offered helpers | |
| | `PREREG_M2_M4.md` | Three methods for helper context, with baselines | M3, M4 |
| | `PREREG_M5.md` | M4 + cheap context-diverse voting | |
| | `PREREG_FM.md` | Execution-verified fact mining for solver code | |
| Published baselines | `PREREG_B1.md` | Label-free selection methods vs the metamorphic check | |
| | `PREREG_B3.md` | Published fixes for distracting / under-specified helpers | |
| | `PREREG_B4.md` | Retrieval / spec-reading methods vs the exact API snippet | |
| Real benchmarks | `PREREG_H1.md` | Do findings survive large inputs and time limits? | |
| | `PREREG_H2.md` | Real contest geometry (CodeContests, Codeforces) | |
| | `PREREG_H2B.md`, `PREREG_H2C.md` | Sampling + label-free checks vs paying for reasoning; MBR-exec | |
| | `PREREG_H3.md`, `PREREG_F2R.md` | Solomon VRPTW (56 instances) | |
| | `PREREG_H4.md` | Helper steering on real contest geometry | |
| | `PREREG_H5.md` | Job-shop scheduling (la01–la40) with CP-SAT | |
| | `PREREG_H6.md`, `PREREG_H7.md` | Newer models (Qwen3.8-27B, Qwen3.6-35B-A3B) | |
| | `PREREG_P1.md` | Are the contest numbers robust to rewording the prompt? | |
| Methods on the hard benchmarks | `PREREG_N.md` | Example augmentation, typed repair, escalation cascades | N2b, N4, N7, N8, N9, N13, N17, N18, N19 |
| | `PREREG_N10.md` | Can the fix be chosen per problem from the first failure? | N11, N12 (agreement gate), N10-M2/M3 |
| | `PREREG_N14.md` | Adapting a verified program when a rule changes | N14b–N14e |
| | `PREREG_N15.md` | Which solver library should the code use? | N15c–N15f |
| | `PREREG_N16.md` | Do token log-probs flag invented API calls? | N16b |
| | `PREREG_V.md` | Validated program reuse; approximate-oracle differential testing | |
| | `PREREG_E3.md`, `PREREG_E3B.md` | A deployable check → sample → think pipeline; model-written brute force | |
| Reuse and distillation | `PREREG_E4_REPLAY.md`, `PREREG_E4B.md` | Distillation with self-replay without forgetting | |
| | `PREREG_B2.md` | Forgetting-mitigation baselines vs self-replay | |
| | `PREREG_D1.md` | Does self-replay carry over to contest geometry? | |
| Beyond computation | `PREREG_X1.md` | Short-answer competition math (MATH-500, AIME) | |
| | `PREREG_X2.md` | Verify once, reuse on GSM-Symbolic variants | |
| | `PREREG_X3.md` | Word problems → optimization models (NL4OPT, IndustryOR) | X4 (Lean 4 / miniF2F), X6 (API fact + thinking) |
| | `PREREG_VIEWS.md` | When can a model catch its own mistakes? Error correlation between views | P4, P5 (PopQA factual QA) |
| Allocating compute | `PREREG_U1.md` | Allocate by failure mechanism vs by difficulty | U1b, U1r (3 seeds), U2 (retrieved facts) |
