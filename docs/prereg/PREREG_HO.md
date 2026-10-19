# Pre-registration HO: does the whole label-free recipe hold on an unseen, harder optimization benchmark?

Written 2026-10-19 18:0x UTC, before any run. Results are appended below without editing this section.

**Why (the decisive test the project still lacks).** Every recipe component was found or tuned on NL4OPT / IndustryOR / MAMO; MAMO was held
out, but its recurring templates favour the program library (FORM2). OptMATH-Bench (100 test problems as shipped with STORM's code; larger
production / scheduling / network / routing MILPs written with many decimal parameters) has never been used here. If the recipe (automatic
fact → two programs + strict check → library → think only on failure) is a real method for 24 GB-GPU models, it must hold here against
always-thinking and the trained specialist STORM, at its cost.

**Setup** (poc/queues/queue_s2_ho.sh; NLOPT_SET=optmath; grader = run_nlopt.correct, as everywhere). Models that fit one 24 GB GPU:
gpt-oss-20b (cheap arms low effort, thinking = medium), Qwen3-14B-AWQ, Qwen3-8B (thinking on, 16k). Arms: mip (no fact, s1), mipf (hand
snippet, s1), mips (automatic fact: the model's own shortest check-passing program from NL4OPT, s1–3), thinks (thinking + automatic fact,
s1–3), then formx (library: the program of the most similar OTHER OptMATH problem from the three models' strict-check-passing mips programs,
s1–3). STORM-Qwen3-4B with its official tool-integrated inference (3 samples) when a GPU frees. Policies as in PREREG_X7 / FORM: CHEAP,
FF, FFR-strict (two programs run, agree and are not 'No Best Solution'; else think), THINK; with mips or formx as the cheap arm.

**Predictions.**
- HO-P1: the automatic fact beats no fact on the cheap program for every model (seed 1), as on X6 / MAMO.
- HO-P2 (main): FFR-strict (mips) is within 3 points of always-thinking at ≤ 50% of its tokens, for each model (seed means).
- HO-P3: the library (formx) raises the cheap program by ≥ +2 points over mips if OptMATH problems recur in type (it is generated from seed
  families), and the FFR pipeline by ≥ +1 at fewer tokens; if problems do not recur, ≤ +1 (as on NL4OPT + IndustryOR).
- HO-P4: STORM is ≥ 5 points above the best 24 GB recipe at ≥ 3 × its tokens (its MAMO lead was +3.0 at 4.4 ×).
- HO-P5 (failure kinds, read from raw programs): most wrong-but-running programs on OptMATH mis-transcribe or drop parameters / index sets
  (large data), not API errors — so facts help less here than on MAMO.
