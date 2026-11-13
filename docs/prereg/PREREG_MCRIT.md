# Pre-registration MCRIT: LLM-Modulo with critics the translations already wrote

Written 2026-11-13 21:0x UTC, before any `mcrit` row exists. Known before writing: every stored trip run of seeds 1–6, the partial LLM-Modulo
rows (PREREG_RW B, 20:5x: every plan that passed the hand-written critics was right), and the offline critic check below.

**Why.** On trips the course ladder's loss sits in the fallback: on the 80 Qwen3-32B trip-seeds (seeds 4–6) where no paid translation reaches
one plan, thinking answers and is right 11 times (FINDINGS 16:5x). In those programs the constraints are mostly read right and the
plan generator fails. LLM-Modulo's critics are complete (written from each trip's structured constraints, so a plan that passes them is the
plan), which a domain-free method does not have. But the ladder has already paid for three programs whose constraints are a model-written
critic set: Qwen3-32B `trc`, gpt-oss-120b `trc`, Qwen3-32B `trct`. Closest prior work: LLM-Modulo (Gundawar et al. 2411.14484) names the LLM
as a possible "critic extractor"; their trip critics come from structured data. Hao et al. 2404.11891 give the solver's UNSAT reasons back; Kambhampati
et al. 2402.01817 find LLM self-critique unreliable, which is why the critics here are executed code, not judgements.

**Offline check (stored runs, seeds 4–6, `results/tmp_tripcritic.py`, `results/np_tripcritic.jsonl`).** Thinking's plan against each program's
constraints; "at least 2 of the 3 programs pass" (any2) was the best rule on these seeds:
- All 300 trip-seeds: thinking's plans passing any2 are right 122 of 128 (95%); 19 of 141 right plans fail it; the gold plan passes it on 232 of 300.
- The 80 fall-through trip-seeds: thinking's plans passing any2 are right 6 of 7; the gold plan passes it on 38 of 80; thinking is right on 11.
So on about half of the fall-through trips the model-written critics accept the gold plan, and thinking finds it on few of them.

**Arm `mcrit`** (`poc/run_plan.py q32 mcrit <seed>`, only the fall-through trips of that seed). Start from thinking's stored plan (its tokens
are already the ladder's). If fewer than 2 of the 3 programs pass it, the failing checks (their source lines, or the program when a check has
no source) go back with "a check can itself misread the task; correct the plan if a failing check states a real requirement", and Qwen3-32B
re-plans while thinking (16,000 tokens), up to 5 rounds, keeping only plan JSON as its earlier turns (as the `modulo` arm). Answer: the first
plan any2 passes; if none passes, thinking's original plan (a right plan the critics reject cannot be lost to a wrong one they also reject).
Seeds 4–6, gpt-oss-120b `trc` as the peer program. Exploratory: the any2 rule was chosen on these seeds.

**Ladders (paired over trip × seed, 300; utility 100 × right − 0.5 × ktok, every step counted).** Current: `trc` → gpt-oss-120b `trc` → `trct`
→ `think`. New: the same, with `think`'s plan passed through `mcrit`.

**Predictions (theory: gain = trips where a re-plan passes any2 × (its precision − the original plan's) − re-plan tokens on all 80).** Right
11 → about 22 of 80; extra tokens about 18k on each of the 80 (three re-plans), 4.8k per trip-seed of 300. **MCRIT-P1:** new − current about
+1.5 utility (+3.7 accuracy), interval including 0. **MCRIT-P2:** plans passing any2 after re-planning are right at least 75%.

**Decision rules.**
- New − current with the interval above 0: fresh seeds 17–19 for the whole ladder, then it enters the trip method; the report states that a
  domain-free critic set narrows the gap to LLM-Modulo.
- Interval including or below 0: closed; the report states that model-written critics are precise when they accept (95%) but too weak to steer
  re-planning toward the plan, and that LLM-Modulo's advantage on trips is its complete, hand-written critics.
