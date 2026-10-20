# Documents

| File | Contents |
|---|---|
| `FINDINGS.md` | Chronological lab log (newest at the end) |
| `prereg/PREREG_<id>.md` | One file per experiment: predictions before the run → results and verdicts |
| `notes/` | Self-critique (CRITIQUE), check coverage (CHECKS), failure → fix map (FIX_MAP), related work (RELATED_WORK), drafts |
| `archive/` | Earlier versions of the proposal |

Commands are in `poc/queues/queue_*<id>*.sh`, analyses in `poc/analyze_<id>.py`.

## Experiments by theme

| Theme | Experiments (`prereg/PREREG_<id>.md`) |
|---|---|
| Why tools distract | E2 predicting new tasks, E4 tool vs needed-algorithm similarity, L1 tools given as a library |
| Handling tool context | M1 tool filter, M2_M4 three methods, M5 voting, FM solver fact mining |
| Published baselines | B1 label-free selection, B3 fixes for distracting tools, B4 retrieval vs exact snippet |
| Real benchmarks | H1 large inputs, H2·H2B·H2C·H4·P1 contest geometry, H3·F2R vehicle routing (VRPTW), H5 job-shop, H6·H7 newer models |
| Fixes on hard problems | N example augmentation, repair, cascades; N10 per-problem fix choice (N12 agreement gate); N14 adapting to a changed rule; N15 solver library choice; N16 log-probs flag invented APIs; V program reuse; E3·E3B check → sample → think |
| Reuse and distillation | E4_REPLAY·E4B self-replay, B2 forgetting baselines, D1 contest problems |
| Beyond computation | X1 competition math, X2 reuse on variants, X3 optimization modeling (X4 Lean proofs, X6), VIEWS when a model can catch its own mistakes |
| Allocating compute | U1 by failure mechanism vs by difficulty (U1r, U2: facts first, then think only on failure) |
| Small models (one 24 GB GPU) | SIZE Qwen3-1.7B to 14B and gpt-oss-20b with the recipe, vs Qwen3-32B (SIZE-CC: contest geometry) |
| Choosing the policy | MODEL: which policy wins where; 30 labelled problems pick it for a new task |
| Facts without a human | X3 (X6-AUTO, X6-VER: the model's own checked program as the fact); X7 held-out MAMO with no hand-written component |
| Proofs | PROOF: Lean 4 (miniF2F) with specialized provers vs general models; geometry proofs with AlphaGeometry's engine (IMO-AG-30, JGEX-AG-231) |

- `docs/SLURM_HANDOFF.md` — state of the project and how to continue it on the Slurm server (2026-10-20); `docs/SLURM_PROMPT.md` — the first prompt for that session.
