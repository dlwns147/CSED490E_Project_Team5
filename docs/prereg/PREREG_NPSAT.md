# Pre-registration NPSAT: does handing the trip's search space to the solver fix the fallback's generator failure?

Written 2026-11-13 19:5x UTC, before any `tr` / `trt` row of Qwen3-32B exists. Known before writing: every stored trip run (seeds 1–6) and
the residual reading of 16:5x (FINDINGS): with the gpt-oss-120b quick step, 69 of Qwen3-32B's 84 wrong answers of 300 (seeds 4–6) are
trips where no translation reaches one plan (80 trips), thinking then answers and is right 14% of the time there; in most fall-through
programs the gold plan is missing from the program's own `candidates()`, and in 61 it breaks none of the program's constraints. The
requirements were read right; the generator (city order, shared flight days) is what fails.

**Why.** The trip method is the course result's weakest cell (72.0% against 93–97% on grids, and more tokens than thinking). On grids the
solver owns the search and the model writes only constraints; in the declarations interface (`trc`, `trct`) the model must also write
`candidates()`, the search space. The CP-SAT interface (`tr`, `trt`, `poc/run_plan.py`, written 11-10 and never run beyond Qwen3-8B dev
pilots) asks only for variables and constraints, so the solver searches city orders and days. If the fallback's failures are the
generator, this interface should settle part of them. Nothing in it is trip-specific (the same prompt asks for "a constraint model").
Closest prior work: Hao et al. 2404.11891 (travel planning as SMT, solver owns the search; a fixed hand-written encoding, not the model's),
LLMFP 2410.12112 (the model writes the full optimization model, five-step), Draft-and-Prune 2603.17233.

**Run (exploratory: seeds 4–6 informed the diagnosis).** Qwen3-32B-AWQ, NaturalPlan trips (100), seeds 4, 5, 6: `tr` (quick, 4,096
tokens) and `trt` (thinking, 16,000), 3 rounds of the harness's count feedback as for `trc` / `trct`. Slurm, 2 × RTX 3090 per job.

**Ladders compared (paired over trip × seed, 300; utility 100 × right − 0.5 × ktok, every step's tokens counted).**
- **Current:** `trc` → gpt-oss-120b `trc` → `trct` → `think` (PREREG_PEERT B, 72.0%).
- **(a) replace:** `trc` → gpt-oss-120b `trc` → `trt` → `think`.
- **(b) add:** `trc` → gpt-oss-120b `trc` → `trct` → `trt` → `think`.
- **(c) quick first:** `trc` → gpt-oss-120b `trc` → `tr` → `trct` → `think`.

**Predictions (theory: the gain is the share of fall-through trips the new step settles × (its precision − thinking's 14%) minus its
tokens on every trip that reaches it).** Qwen3-8B's pilot (count 1 on 1 of 30 quick CP-SAT translations, "orders the cities in its head
and misplaces the shared flight day") says the model may fix the order itself in either interface. I expect `trt` to settle about a quarter
of the 80 fall-through trips at about 80% precision: +4 accuracy, −1.6 utility in tokens. **NPSAT-P1:** (b) − current is about +2 utility,
interval including 0. **NPSAT-P2:** (a) − current is within ±3 (the two interfaces fail on overlapping trips). **NPSAT-P3:** (c) adds less
than +1 (quick translations of trips fail the generator in both interfaces).

**Decision rules.**
- Any of (a)–(c) above current with the interval above 0: run that ladder once on fresh seeds 17–19 (all its steps) before it enters the
  trip method.
- None: closed; the fallback's failure is not fixed by giving the search to the solver, and the course report states the trip residual as
  the model's reading of a plan's shape, with the measured counts.
- Either way, report how many of the 80 fall-through trips `trt` settles, and how often its plans keep a wrong city order with every
  stated requirement met (the 16:5x reading, in this interface).

## Result (written 2026-11-14 06:0x UTC; `python3 poc/gp_conj.py npsat`, Qwen3-32B seeds 4–6, 300 trip-seeds, corrected thinking rows)

| Ladder | Accuracy | Tokens per trip-seed | − current, utility |
|---|---|---|---|
| Current (`trc` → gpt-oss-120b `trc` → `trct` → `think`) | 73.0% | 18.2k | — |
| (a) `trt` in place of `trct` | 66.0% | 22.0k | **−8.9 [−13.2, −5.2]** |
| (b) `trt` added after `trct` | 73.0% | 24.0k | **−2.9 [−3.6, −2.1]** (NPSAT-P1) |
| (c) `tr` before `trct` | 73.0% | 19.9k | **−0.8 [−1.0, −0.7]** (NPSAT-P3) |

NPSAT-P1 (about +2, interval including 0) is wrong: −2.9 with the interval below 0. NPSAT-P2 (within ±3) is wrong: −8.9. NPSAT-P3 (less
than +1) holds. **Decision: closed** (no ladder above current). On the 80 fall-through trip-seeds `trt` settles 2 (1 right), `tr` 0. The
CP-SAT interface fails before any search: `trt` reaches one plan on 55 of 300 (52 right) against `trct`'s 197 (190 right); 199 of its 300
programs never run after 3 rounds (KeyError 41, NameError 32, AttributeError 31, TypeError 21, IndentationError 19, other API misuse), and 27
overflow the 32,768-token window during feedback rounds. `tr` (quick) runs on 2 of 300. So the measured residual is not the solver's search: the
model cannot write a working CP-SAT model of a trip in 3 rounds, and in the declarations interface, where it can, it misreads the plan's shape.
