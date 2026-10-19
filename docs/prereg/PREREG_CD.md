# Pre-registration CD: is the knowledge in a fact transferred by working code but not by a description of the same content?

Written 2026-10-19 21:0x UTC, before running. Results are appended below without editing this section.

**Why (the mechanism that would unify the project's findings).** Three results point the same way: (1) API facts — a list of the library's
names hurts (X6-AUTO) while a 6-line usage snippet fixes the crashes (X6); (2) formulation facts — a hand-written sentence describing the
correct Miller-Tucker-Zemlin constraints is misapplied (TSP 50–68% → 0–6% for Qwen3) while a checked program of a similar problem fixes it
(FORM); (3) approach — the model's own natural-language plan makes gpt-oss-120b worse on contest problems (CH, −5.8). But none of these
compared the SAME content in the two forms: the name list and the plan carry less information, and the checked program carries more.
**Hypothesis:** models apply knowledge given as working code and misapply the same knowledge given as a description.

**Matched pairs** (same facts, two forms; prompts in poc/run_nlopt.py SNIP / SNIP_TEXT and poc/run_form.py CODE / FACT):
- K1 API usage, NL4OPT + IndustryOR (345): no fact (mip, existing) vs the pywraplp snippet as code (mipf, existing) vs the same snippet
  described in words (mipt, new: CreateSolver, IntVar / NumVar, Add, Maximize / Minimize, Solve + OPTIMAL, Objective().Value()).
- K2 TSP formulation (34 MAMO travelling-salesman problems) and K3 supply redistribution (16 MAMO problems): base = the mips prompt (existing),
  + the sentence (formh, existing), + the same constraint written as 4–5 lines of OR-Tools code (formc, new).
- gpt-oss-20b (low), Qwen3-14B-AWQ, Qwen3-8B; seeds 1–3 (paired by seed); poc/queues/queue_s2_cd.sh, GPU1.
**Predictions.**
- CD-P1 (formulation, the core test): code ≥ sentence + 15 points on K2 and on K3 for each model (seed means), and code ≥ base + 15 on K2
  for gpt-oss-20b (base 0–3%).
- CD-P2 (API): the description is better than no fact but ≥ 3 points below the code snippet for the two Qwen3 models on K1; equal within
  2 points for gpt-oss-20b (it rarely makes API errors).
- CD-P3 (how it fails): with the sentence, the raw programs implement the constraint wrongly in a way the code form rules out (e.g. excluding
  the start city only on one side, as seen in FORM); with code they copy the loop structure. Read ≥ 10 programs per form.
If CD-P1 fails (the sentence is as good as code when the content is matched), the earlier contrasts were about information, not form, and
the "give working code" lesson is withdrawn.
