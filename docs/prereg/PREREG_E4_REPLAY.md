# Pre-registration: E4 (PROPOSAL 4.3), distillation with replay: can per-task robustness be learned without damaging an unseen task?

Written 2026-10-13 13:00 UTC, before generating the replay data or training any model. Results are appended below without editing this section.

**Background (F5 / FINDINGS E5b, E5c).** A LoRA distilled from Qwen3-8B-with-thinking programs (K0/K4/K8 prompts) makes the no-thinking
8B robust to extra helpers on the trained tasks, but damages unseen tasks: trained on area2/pip/segs/close, the unseen hull drops from
97 to 34 on clean (K0) prompts; adding teacher data for 5 more tasks (9-task LOTO) does not help (28). Fine-tuning moved the model off
its own idiom (Graham-scan variants and improvised loops instead of the monotone chain it wrote before).

**Hypothesis.** The damage comes from pulling the student toward the teacher's program style; replaying the student's OWN verified
programs on other tasks anchors its style and protects an unseen task. More teacher data on the same other tasks does not.

**Design (leave-hull-out; hull is never in any training set).** Qwen3-8B, LoRA r = 16, α = 32, lr 1e-4, 2 epochs, effective batch 8
(poc/sft_lora.py, unchanged hyper-parameters), all on the new server stack:
- **A (no replay):** the E5b leave-hull-out data: 600 verified thinking-teacher programs on area2 / pip / segs / close, K0/K4/K8 thirds.
- **B (self-replay):** A + 300 programs written by the base 8B WITHOUT thinking on K0 prompts of the 5 other geometry tasks (convex, tri,
  overlap, lattice, rectunion; training instances, correct on all 8 variants), 60 per task.
- **C (teacher replay):** A + 300 thinking-teacher programs for exactly the same 300 prompts as B (same tasks, instances, K0 toolbox).
B and C differ only in who wrote the extra programs.
**Evaluation** (no thinking, T = 0.7, `--stdlib`): hull K0 and K8, seeds 1–2 (120 programs each); the 4 trained tasks under K8, seed 1
(240; in-task gain); unseen new tasks diameter (no toolbox) and delaunay (fixed in_circle helper), seed 1 (60 each; base = the E2 runs).

**Predictions.**
- E4-P1: B protects hull on clean prompts: hull K0(B) ≥ hull K0(A) + 30 points.
- E4-P2: it is the self-written data, not more data: hull K0(B) − hull K0(C) ≥ +20 points.
- E4-P3: the in-task robustness survives replay: trained-task K8 accuracy of B within 3 points of A (A expected ≈ 98).
- E4-P4 (uncertain): on the other unseen tasks (diameter, delaunay-fixed) B ≥ A.
Paired 95% bootstrap CIs over instances. A failure of P1 means self-replay on other tasks does not protect unseen tasks.


---
## Results (appended 2026-10-13 12:50 UTC; predictions above unedited)

**Deviation (before training B/C):** the no-thinking 8B is rarely correct on tri / lattice / rectunion, so with 6 sampling seeds the matched
replay set has 270 examples, not 300 (convex 60, overlap 60, rectunion 60, tri 59, lattice 31); B and C use exactly the same 270 prompts.
Arm A's data selection is identical to E5b's (same 600 examples). `poc/analyze_e4.py`; base = the untuned 8B on the same stack and prompts.

| eval (correct on all 8 variants) | base 8B | A: no replay | B: self-replay | C: teacher replay | B − A | B − C |
|---|---|---|---|---|---|---|
| hull, K0 (unseen task; 2 seeds, 120) | 109 | 48 | **118** | 36 | **+58.3** [+49.2, +67.5] | **+68.3** [+60.0, +76.7] |
| hull, K8 (unseen task) | 23 | 25 | 31 | 14 | +5.0 [−5.0, +14.2] | +14.2 [+5.0, +23.3] |
| 4 trained tasks, K8 (240) | 225 | 236 | **240** | 240 | +1.7 [+0.4, +3.3] | 0 |
| diameter, no toolbox (unseen, 60) | 54 | 60 | 60 | 60 | 0 | 0 |
| delaunay, fixed helper (unseen, 60) | 55 | 59 | 47 | 45 | **−20.0** [−31.7, −8.3] | +3.3 [−11.7, +18.3] |

- **E4-P1 confirmed:** self-replay keeps the unseen hull task intact (118/120 vs 48/120 without replay; base 109).
- **E4-P2 confirmed, strongly:** with the same 270 prompts written by the thinking teacher instead, hull K0 is 36/120, worse than no replay.
  Who wrote the replay programs decides the outcome, not how many tasks are covered.
- **E4-P3 confirmed:** the in-task K8 robustness is kept (240/240).
- **E4-P4 not confirmed:** on delaunay both replay arms are worse than A (B −20.0; C −23.3). B's 13 failures are all the same off-by-one
  when reading the triangle section of stdin (`data[1 + n + i]`), C's are logic / degenerate errors. Diameter is unaffected (60/60 everywhere).
- **Mechanism, read from the programs (hull K0):** the base model writes the monotone chain in 120/120 programs, B in 120/120, A in only
  59/120 and C in 49/120 (the rest are angle-sorting Graham variants and improvised loops). Distillation from the teacher moves the student
  off its own idiom on tasks it never trained on; replaying the student's own programs anchors that idiom. Teacher programs on other
  tasks do not anchor anything, they pull further.
