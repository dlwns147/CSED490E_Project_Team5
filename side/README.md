# Side project: proofs

The side project is **proofs**: getting exactly right proofs from open models at low cost, in natural language, in Lean, by translation
into a symbolic engine, and by computing an object that proves a statement exists. Everything about it is recorded in this folder, with
the status and the dated log in this file. Decisive runs are pre-registered in `docs/prereg/PREREG_SIDE.md`.

Side work may use the Slurm server's GPUs: a model server and client commands run as one job through `poc/slurm/job.sh` and
`poc/slurm/lane.sh` (see the root `README.md`, section on Slurm).

**Working rules:**
- Work in a fork, or on a branch of this repository. Add files under `side/`, and don't change `poc/` scripts.
- Before any run that decides something, add a pre-registration to `PREREG_SIDE.md`: why, design, predictions, decision. Never edit a
  prediction afterwards; append dated results under it.
- Never commit model outputs, logs, benchmark texts, server addresses or keys. `*.jsonl` and `*.log` are ignored on purpose.
- Read `PROJECT.md` §1 for the goal: exactly right answers at the lowest cost, utility = 100·right − 0.5·(thousand output tokens).

## Where it stands

| Route | State | Hardest open gap |
|---|---|---|
| Geometry by translation (`geo_translate.py`, `geo_decl.py`, `geo_closure.py`, `geo_check.py`) | Kernel-checked in Lean: **263 of 263 HAGeo-409 rows, 126 of them with no figure reading** (HAGeo 263 at K = 2,048, 287 at K = 8,192); held out **22 of 65**; **27 of IMO-AG-30** (all kernel-checked); held-out faithfulness read by hand (16 whole problems, 6 one direction or part), declarative statements | **Telling a faithful statement from an unfaithful one without a human:** agreement fails on declarative statements, half translations leave no trace, and some translations assume the claim (SIDE-GT-REDUCE attacks the last). Most proofs read a configuration from the figure. IMO 2008 P6, 2011 P6 and 2021 P3 need theories the engine lacks |
| Natural-language proofs | Computational checks of a proof failed (SIDE-PF, SIDE-PG) | A free check that sees a step left unjustified while true, the most common error |
| Lean (main track, `PREREG_PROOF.md`) | A specialised 8B prover is best; the compiler is a perfect check | Not a side-project gap at present |
| Constructions (`construct.py`) | Unsolved for an 8B model; its own checker is not a usable free check | A derived free check, or a search the problem's structure makes exact |

**Running now (geometry):** nothing; SIDE-GT-MG finished 2026-11-08 11:5x UTC.

## Goal for the teammate (set 2026-11-11)

The proof part is a bounded deliverable, not an open research track. The results above are frozen as the proof section of the report; the
work left is one or two well-specified algorithm tasks, each with frozen inputs, one scoring command and a baseline number. We prepare these
kits, run anything that needs a model, and read every result with you.

**The goal:** from the same frozen translations, more problems end with a machine-checked proof, at no added model cost. It is the
project's goal (exactly right at the lowest cost) on the side that needs no ML: the model's tokens stay fixed, and only CPU time may grow.

**Task 1, the fresh-figure solver.** On MechGeo's 44 IMO problems, 13 whole problems are counted in each arm: a faithful statement, proved,
its certificate accepted, and its goal held on 8 of 8 fresh figures. 8 more problems are proved and certified but lose only because the
figure solver built fewer than 8 fresh figures (9 statements per arm got none). Every figure that was built satisfied the goal.
- Metric: whole problems counted by that rule, per arm (now 13; at most 20 and 21 if every lost problem gets its figures).
- Constraint (soundness): the rule may not get weaker. A fresh figure must satisfy every hypothesis to tolerance, differ from the first
  figure, and be non-degenerate; the known false proofs (IMO 2011 P6 and the controls in `PREREG_SIDE.md`) must still be rejected.
- Cost: CPU seconds per statement, reported next to the count.
- Before running it, pre-register a predicted count with a decision rule (we write it together).

**Task 1 kit** (`side/kit_fresh.py`; frozen inputs in `nlp_data/geo/kit_fresh/`, not in the repository: both arms' certificates,
the verdicts, and the checker's results, 73 of 78 and 78 of 82 accepted as registered).
- Run: `python side/kit_fresh.py <kit dir> [--solver <your module>] [--only <problem id>]`. It prints, per arm, the whole problems counted,
  the faithful certified problems lost at the fresh-figure rule, and CPU seconds per statement.
- Soundness control: `python side/kit_fresh.py <kit dir> --control [--solver <your module>]`. It scores 267 planted false steps
  (`plants.json` in the kit dir): each is a proof step that holds exactly on a proof's figure moved to a coincidence, and is false in
  general. A sound solver counts none of them whole. If your `figures` takes a keyword `ref`, the kit passes the proof's figure.
- Your part: a module with `figures(dsl, n, seed)` that returns candidate figures (lists of complex coordinates in the statement's point
  order, `geo_decl.parse`). The kit, not your solver, decides what counts as a fresh figure: every hypothesis and order condition holds, the
  points are apart, the configuration (orientation of unsigned angles) is the proof's own, there are no more chance collinearities than on the
  proof's figure, and the figure is not similar to one already accepted. Then the proof's auxiliary points are rebuilt and every step must hold.
- Baseline (the stored run): 13 whole problems per arm. Lost at the rule: NL 7 problems (IMO 2005 P1, 2007 P2, 2012 P1, 2015 P4, 2019 P6,
  2023 P2, 2025 P2), LEAN 8 (IMO 2000 P1, 2007 P2, 2012 P1, 2013 P4, 2015 P3, 2015 P4, 2019 P6, 2023 P2). Several statements got 0 fresh
  figures; others got 1 to 7. The default solver is `geo_decl.solve` (least squares from 240 random starts, generic figures first).
- Kit checked (2026-11-11 17:0x UTC): the default solver run through the kit reproduces the stored count exactly, 13 whole problems per arm, with the
  same 7 and 8 problems lost, at about 84 CPU s per statement (58 NL and 61 LEAN statements, 8 workers). The kit is ready to hand over.
- Where to start: why `geo_decl.solve` returns few figures on these statements (few starts converge; or the converged ones are rejected as
  degenerate or of another orientation), then a solver that samples the solution set directly, for example by moving along it from one
  solution found.

**Task 2, only after task 1:** HAGeo-409 coverage (263 of 409 now; HAGeo reports 287, random points 218), a public benchmark with
published numbers, so any gain compares directly.

**Plan (2026-11-13): the teammate codes both tasks (Plan A).** The teammate is a computer scientist in computational algorithms who codes;
both tasks are algorithm problems with no model in them, so they are the teammate's to own, with us running anything that needs a model and
reading results together.
- **Task 1 is the warm-up (about a week).** A reference walk solver already exists outside the repository (it starts from the proof's figure
  and moves along the solution set): 20 and 21 whole problems, 0 of 267 plants counted, through the kit. The teammate writes their own solver
  without seeing it; the bar is that count with no plant counted, at lower CPU time. The open algorithmic part is the tolerance: on IMO 2019 P6
  a true angle fact has numerical error 6e-7 against the kit's 1e-6, so a certified check (interval arithmetic or high-precision Newton
  refinement of each figure) instead of a fixed tolerance would make the rule exact.
  Checkpoints: (1) the default solver through the kit reproduces 13 / 13; (2) the new solver, count and CPU s per statement; (3) `--control`
  counts 0 plants.
- **Task 2 is the main contribution.** `python side/geo_closure.py run <rows> <out> --k K` proves HAGeo-409 rows on CPU; 263 now, HAGeo 287,
  AG1 177, random points 226 on our engine. Two algorithm problems, both scored by rows proved and CPU time on a public benchmark:
  (a) choosing auxiliary points (our greedy beats random by +37; HAGeo's larger budget reaches 287), a search problem over candidate
  constructions; (b) the 146 rows left: 178 of the readings left need facts the engine never derives (order of points on a line or circle,
  side-side-side pairs), i.e. new inference rules or a decision procedure for them. We prepare a task-2 kit (frozen rows, one scoring
  command, the 263 baseline, the soundness controls) the same way as task 1.
- What the report needs from the proof part: the frozen results above, plus whatever tasks 1 and 2 add, written and presented by the teammate.

**Boundary (2026-11-13, second pass; the teammate codes with Codex and runs jobs on the Slurm cluster).**
- **The line is the frozen formal statement.** Everything before it involves a model and stays with us: natural language → statement,
  faithfulness, any LLM call, the translations themselves (frozen in `nlp_data/geo/`). Everything after it is the teammate's: building
  figures, proving, certificates, Lean export and checking, CPU cost. The teammate needs no GPU and no model; if a task seems to need a model
  call, it comes to us.
- **The judge is a kit, not the code.** Each task has frozen inputs, one scoring command, a baseline and a soundness control (planted false
  steps that must stay rejected). Code written with Codex is accepted when the kit says so; work lives under `side/` (or a branch), never in
  `poc/`; a predicted number and a decision rule go into `PREREG_SIDE.md` before each decisive run.
- **Cluster:** CPU partitions only (`sbatch -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none poc/slurm/job.sh '...'`, the project
  image has Python and Lean); proofs and Lean compiles are CPU jobs.

**Where the room is (11-13), after checking what exists.** General geometry provers are crowded: AlphaGeometry 1/2, Newclid, TongGeometry
(30/30 on IMO-AG-30), HAGeo (28/30, CPU), Wu's method + deduction (21/30 on a laptop; with AlphaGeometry 27/30, Sinha et al. 2404.06405).
A new general prover would not beat them. Figure sampling (task 1) is a solved area too (homotopy continuation, Bertini, certified points).
What our pipeline has and theirs do not is a **Lean-checked theorem for every counted proof**. So the room is certified proofs where our
linear engine stops:
1. **Main: a certified algebraic fallback.** Every HAGeo-409 goal is a polynomial equality (coll 144, cyclic 82, cong 59, perp 50,
   eqangle 27, para 25, midp 9, eqratio 7, simtri 5, contri 1), so Wu's method or Gröbner bases apply to all 146 rows our engine leaves.
   The proof is an identity goal = Σ cᵢ·hᵢ, which Lean checks by `linear_combination` (Mathlib's `polyrith` already gets such coefficients
   from SageMath; Pottier and Théry certified Gröbner geometry proofs in Coq in 2008–2011). So the new part is not the idea but making it work
   on a modern benchmark with honest side conditions. Two algorithmic problems: (a) non-degeneracy conditions must become explicit, readable
   hypotheses, not hidden generic-case assumptions; (b) reducibility: an incenter or a "second intersection" has several algebraic solutions
   and the goal may hold on only one, so the component must be chosen, and our numeric figure says which one. Score: extra HAGeo-409 /
   IMO-AG-30 problems with a kernel-checked theorem, CPU time, and the side conditions each theorem assumes.
2. **Lean checking cost.** Some exported theorems need far beyond the 1,200 s limit (8 needed up to 7,457 s): shrinking certificates or the
   proof terms is a measurable systems task.
3. **Task 1 (fresh figures)**, a few days with existing tools, or we finish it with the reference walk.
Out of scope for the teammate: point-order facts (inequalities need real algebraic geometry, e.g. CAD), translation and faithfulness.

**Target that beats related work (11-13, third pass).** HAGeo-409 is the one benchmark where the best published number is beatable on CPU:
HAGeo (2512.00097, ACL 2026) proves 287 of 409 at K = 8,192 candidate sets (263 at K = 2,048; random points 218; AG1 177), with no proof
certificate; no other system reports on it. We prove 263 with a certificate for each, most also as Lean theorems. **Goal: more than 287
counted rows, each certified, at no more CPU than HAGeo's setting (64 cores, 60 s per DDAR run).** Why it is within reach, lever by lever:
- **HAGeo's own heuristic inside our closure.** Our candidates are random one-step constructions ranked by measured rank gain
  (`geo_translate.aux_candidates`); HAGeo keeps a point only if it lies non-trivially on a line or circle of the figure, and that alone takes
  them from random 218 to 287. Our closure tests a whole pool at once (monotone: every subset's proofs are in it), so better candidates cost
  nothing extra in search. **Their code is not public** (checked 11-13: github.com/boduan1/HAGeo holds the README and figures only, "full
  code is under review by Microsoft"; the benchmark is public), so the rule is re-implemented from the paper's description.
- **A faster closure, so larger pools fit the same CPU** (incremental span updates, cheaper numeric fact enumeration).
- **The algebraic fallback** (lever 1 above) for rows whose missing facts are non-linear relations: Wu's method alone solves problems deduction
  cannot (15 of IMO-AG-30, some unsolved by AlphaGeometry, Sinha et al.), and nobody reports it on HAGeo-409.
- **Compute headroom.** Our 263 used 1,800 s on one core per row (136 rows timed out; median 1.8 s on proved rows); HAGeo's 287 used up to
  8,192 attempts of 60 s on 64 cores. Matching HAGeo's CPU gives the engine one to two orders of magnitude more time per row, so the first
  measurement is simply our engine with more restarts and cores (Slurm CPU partitions), before any new idea.
Checkpoints, each through the task-2 kit and pre-registered: (0) reproduce 263, then the same engine at HAGeo's CPU budget; (1) HAGeo's heuristic as the candidate source; (2) the faster
closure at matched CPU; (3) the algebraic fallback on what is left; (4) certificates and Lean export of every new row. Each step reports rows
proved, CPU time, and rows lost or gained by difficulty band (HAGeo reports 40.8% on its hardest [4, 5) band at K = 2,048).

**Measured room, lever by lever (11-13, from stored runs; the task-2 kit judges every new number).** No result on HAGeo-409 after HAGeo's
has been published (searched 11-13), so 287 is the bar.

| Where | Rows | What it takes | Measured |
|---|---|---|---|
| Our gap to HAGeo by band | −9 [1, 3), −9 [3, 4), −8 [4, 5), 0 [5, 6), 0 [6, 7] | the gap is all below difficulty 5: rows HAGeo reaches and we time out on | per band, SIDE-GT-H409 |
| Statements that do not build | 6 (difficulty 1.0–3.3) | `eq_trapezoid` (4) and two `IndexError` in our language | a language fix, then the same engine |
| Greedy and random points as a portfolio | +8 at 2 × 1,800 s | run both searches; the random arm proves 8 rows the greedy misses | **271** counted (union of the two stored runs) |
| More CPU, same engine | 100 of the 146 rows at 16 × 1,800 s | nothing new | **+16 counted → 279** (predicted 288); 2 × / 4 × / 8 × / 16 ×: +9 / +10 / +14 / +16, flattening; 7 of 23 certificates refused by the kit (SIDE-GT-H409-CPU) |
| HAGeo's candidate rule | unknown | re-implement from the paper | checkpoint (1) |
| Algebraic fallback | the 146 left: median difficulty 4.5, 11 points; 65 collinearity goals; **63 use an incenter** (vs 22% of solved rows) | an incenter or excenter is one of four algebraic branches, so the proof must pick the component the figure shows | checkpoint (3) |

**Task 2 kit** (`side/kit_h409.py`; frozen inputs in `nlp_data/geo/kit_h409/`, not in the repository: the 409 rows, the 266 reference
certificates, the reference count and times).
- Score: `python side/kit_h409.py score <kit dir> <your cert dir> [--times <your run rows .jsonl>]... [--cores C] [--workers W]`. A row counts
  only from its certificate: bound to the frozen statement (same statement, same goal, every fact about the statement's points given by the
  construction, read up to point order and merged lines and circles), accepted by `geo_check.py`, and every step and the goal true on 8 of 8
  fresh figures. It prints the count by band, rows gained and lost against the reference with a sign test, and CPU from your run rows.
- Soundness control: `python side/kit_h409.py control <kit dir>`: 737 tampered certificates (a false goal; the false goal also assumed as a
  fact; one coefficient doubled). A sound judge counts none. If you add a new kind of proof step, extend `geo_check.py` and this kit together
  and the control must still count 0.
- Kit checked (2026-11-13 14:4x UTC, jobs 1436350 and the control rerun): it reproduces the reference count exactly, **263**, losing the same
  3 proved rows to fresh figures (2016 IranGOA P1, 2017 CTST P14, 2020 AQGO P3); the control counts **0 of 737**. Two kit faults were found
  and fixed on the way: Newclid lists a different subset of each circle's facts from build to build (binding now reads merged circles), and
  a plant with a repeated point is degenerate, not false. `geo_check.py` alone rejects all 266 false goals; the kit's binding is still needed
  because the checker takes the certificate's statement facts as given.

**Suggested split for the teammate (11-13, fourth pass), in order, each a coding task with a number to beat:**
1. **Warm-up inside task 2 (days):** the missing constructions (`eq_trapezoid`) and the two build errors, then the greedy + random portfolio.
   Expected 271–277 counted; this alone passes HAGeo at K = 2,048 (263).
2. **HAGeo's heuristic, re-implemented from the paper** (points that lie non-trivially on a line or circle of the figure) as our candidate
   source, at matched CPU against the 16× curve. Their random → heuristic step was +69 rows in their engine.
3. **The algebraic fallback with component choice** on the rows still left: Wu's method or Gröbner bases, the branch (incenter vs excenters,
   which intersection) fixed by the numeric figure, non-degeneracy conditions written out, the identity checked in Lean by
   `linear_combination`. This is where certified proofs go beyond what HAGeo reports.
We keep: translation and faithfulness, the kits, any model call, and reading each result with the teammate.

**Out of scope:** telling a faithful translation from an unfaithful one without a human, translation and prompting, and new benchmarks.
They stay as future work in the report.

## Background for the teammate

Our side of the proof work was testing and analysis only from 2026-11-07; since 2026-11-11 we also prepare the task kits above and review the results with you. Numbers marked *pending* come from runs still going and are filled in here when they end.

**What exists.** A model translates a geometry problem into a declarative statement (`geo_decl.py`). A least-squares solver builds figures of it, and a CPU engine proves it by linear algebra over directions, log lengths and squared lengths (`geo_closure.py`). An exact Python checker tests the proof (`geo_check.py`). `geo_lean.py` writes each proof as a Lean theorem over the rule library in `side/lean/` (Lean 4.15.0 with the matching Mathlib; no `sorry`, standard axioms only).

**Export default:** `--lift` since 2026-11-07.

**To reproduce one theorem.** From a certificate directory: `python side/geo_lean.py all <certs> <out> --lift`, then compile each file with `LEAN_PATH` holding Mathlib and the compiled `side/lean/` modules, built in the order GeoBase, GeoRules, GeoSim, GeoCircle, GeoCert, GeoLift. A theorem takes a median of 22 s; a few need far longer than the 1,200 s limit. `python side/geo_decl.py rread <certs> <out.jsonl>` tests each reading on the statement's figures.

**What the tests say.**

| Question | Answer so far |
|---|---|
| Can the kernel accept the engine's proofs? | Yes: 348 of 350, and no step rejected. The other 2 rest on a figure constant. 8 of them needed a 4-hour limit, up to 7,457 s |
| IMO-AG-30 | All 27 problems we solve have a kernel-checked theorem (69 theorems), 7 of them with no reading before lifting; lifting wasn't run on this set. AlphaGeometry2 and TongGeometry reach 30 |
| Can a reading be proved? | Often. With directions modulo 2π, **126 of 263 counted HAGeo rows** have a kernel-checked theorem with no reading (from 48). Held out, 46 of 82 theorems (from 15), on 11 faithful problems (from 2). Lifting fails on 11 of 344 by Lean's limits or the exporter, never by a rejected step, and the unlifted theorem stands |
| Do readings ever fail? | Unknown for most. The search reaches 4 or more of 40 starts on only 48 of 246 readings, so "no figure" is weak; among those 48 the only flips are the removed ISL 2016 family. With order conditions dropped, 16 of 185 flip and the goal fails on all 16, so order conditions carry real weight |
| Can the engine do without the rules that need readings? | Mostly: 69 of 84 held-out statements are proved without them (15 time out), covering 20 of 25 problem ids. Not certified or compiled; the HAGeo half was withdrawn |
| Does "no reading" mean nothing was read from the figure? | **Not always.** A statement with an unsigned angle (`uangle`) becomes a directed `EqA` with the sign taken from the figure, and that is a hypothesis of the theorem. 26 of 82 held-out theorems have one, 10 of the 46 with no `Read`, so the faithful problems with neither number 8. HAGeo-409's statements have none |
| Is the translation faithful? | Still read by hand on our side: 22 of 65 held out. On MechGeo's 44 audited IMO statements, giving the model the audited Lean statement doesn't help: 13 whole problems either way (SIDE-GT-MG). MechGeo without a human: 29 of 43 |

**Where to work, hardest first.**
1. **Faithfulness without a human.** This is the real limit. Agreement between translations helps, but a wrong statement can still be proved. MechGeo (2608.02295) refuted 22 statements experts had accepted, and our figure solver can't see such errors.
2. **The readings left, and unsigned angles.** On HAGeo, 178 of the 273 left aren't in the row space at all, so the relation they need was never derived: they need the order of points on a line or a circle, or belong to side-side-side pairs with no angle relation. The other 95 are in the row space modulo π but not modulo 2π, and the rows that block them are mostly givens (collinearity 84, equal angles 56, perpendicular 42) and isosceles rows (60). Order facts could enter as hypotheses of the statement.
3. **Coverage.** On one engine, random points prove 226 of 409 and our greedy choice 263 (+37, 95% interval [+23, +51]); random finds only 8 rows the greedy misses. The greedy earns its place, but 146 rows remain, and HAGeo reaches 287 at its largest budget.

**Don't retry without a new idea:** model-proposed auxiliary points (they prove nothing random misses), computational checks of natural-language proofs, or the proof list in place of the triple search (circle tangency can't be written yet).

**Where things are.** Status and dated log below; predictions and verdicts in `docs/prereg/PREREG_SIDE.md`; prior work in `docs/notes/RELATED_WORK.md`.

## Log

**2026-11-12 17:4x UTC: the kit now has a soundness control, and both solvers pass it; the walk counts 20 and 21 through the kit (a reference run, not the registered task-1 run).**
- **Why:** task 1 needs a check that a new solver does not weaken the rule, in the kit's own format; the stored false proof (IMO 2011 P6) is in an older format.
- **Kit changes** (`side/kit_fresh.py`): `--control` (above); the proof's figure is passed to a solver that takes `ref`; fact kinds the
  numeric check does not know are rejected (none occur, so no count changes); `--workers` works for any solver.
- **Count through the kit:** the default solver still gives 13 and 13 with the same 7 and 8 problems lost (68 CPU s per statement),
  so the changes leave the stored count as it was. The walk (`nlp_data/geo/kit_fresh_probe/walk_solver.py`, outside the repository)
  gives **20 (NL) and 21 (LEAN), none lost**, at 71 CPU s per statement, most of it building the proof's own figure. This is task 1's expected answer.
- **Control (267 plants on 91 statements, 3 per statement at most; the proof's figure moved by a median 2e-4 to make each step hold exactly):**
  the walk counts **0** whole and gives 8 figures for every plant, so every plant was tested and rejected. The default solver also counts
  0, but gives fewer than 8 figures on 125, so on those it rejects for lack of figures, not by testing.
- Plants were kept only if false by more than 1e-4 on some figure, which excludes the three IMO 2019 P6 facts that were wrong only by numerical noise.

**2026-11-12 15:2x UTC: planted false steps: the walk's nearer figures still expose every false step tried, so nearness is not a soundness problem for task 1 (probe, not the registered run).**
- **Why:** the walk's figures sit nearer the proof's figure (entry below; the nearest accepted one is under 0.01 on 8 of 41 statements). A false step could pass on figures that all lie close to the figure it was found on. Prediction, written before the run: no false step missed by either solver.
- **Setup:** all 119 faithful, certified statements, both arms (Slurm jobs 1398661–2). Each solver's figures are the 8 the kit would accept. Two kinds of plant:
  - **Near-coincidences:** every para, perp, cong, eqangle, eqratio and cyclic fact over the statement's points that is off by less than 1e-4 on the proof's figure (the false 2011 P6 proof rested on 7e-5), and is false: it fails at the kit's tolerance (1e-6) on the proof's figure or on some accepted figure. A solver misses one if all 8 of its figures pass it.
  - **Exact coincidences:** for the 3 false facts per statement that vary least over the default figures, move the proof's figure along the solution set until the fact holds exactly, treat that as the proof's figure, and draw 8 new figures from there. This is a proof found on a coincidental figure.
- **Result:**

  | | default solver | walk |
  |---|---|---|
  | statements with 8 figures | 66 | 119 |
  | false near-coincidences missed | 0 of 15,972 | 0 of 35,499 |
  | of which pass the proof's figure at 1e-6 | 0 of 1,395 | 0 of 1,970 |
  | exact-coincidence plants exposed | 156 of 156 | 277 of 280 |

  The 3 the walk did not expose (IMO 2019 P6, NL) are not false. They are true angle facts whose numerical error reaches 6e-7 on some figures, close to the 1e-6 tolerance, so they were labelled false by noise. The walk exposes 269 of its 277 plants on all 8 figures.
- **What it means for task 1:** a walk-style solver keeps the check sound; its figures need not be as far apart as the default's. The kit's 1e-6 tolerance is close to the numerical error on IMO 2019 P6, so a true step can fail there by noise. Task 1 should report the largest deviation of the proof's own steps on its figures.
- **Kit gap found:** `geo_closure.num_fact` passes any fact kind it does not know. No stored certificate uses one (checked: every kind in the 119 certificates is handled, apart from the skipped bookkeeping rows), so no count changes, but task 1 should reject unknown kinds.
- Addition to the entry below: per statement, the nearest accepted walk figure has median distance 0.033 (default 0.60), not counting copies of the proof's own figure, which the kit rejects.
- Script: `nlp_data/geo/kit_fresh_probe/plant.py` (outside the repository, as before).

**2026-11-12 12:5x UTC: task 1 diagnosed: the default solver rarely lands on the solution set; a walk along the set from the proof's figure gives 8 fresh figures on every lost statement (a difficulty probe, not the registered task-1 run).**
- **Why:** to judge how hard task 1 is before handing it over.
- **Root cause:** on the 41 faithful, certified statements of the 15 lost problems (7 NL, 8 LEAN), least squares from random starts converges on only 1–8 of 240 starts (1 on 15 statements). Every figure it does find passes the kit's rule. So the loss comes from too few starts landing on the solution set, not from figures being rejected. Up to similarity, the set has dimension 1–3 (2 on 25 statements), inside 14–22 coordinates.
- **Probe:** from the proof's own figure, take a random step in the null space of the hypotheses' Jacobian (the tangent space of the set), then least squares back onto the set. Repeat from figures already accepted.
- **Result:** on all 41 statements, 8 fresh figures pass the kit's rule, and the proof holds on all 8. That takes 1–6 s per statement, against 107 s for the default solver. All 15 lost problems would count, so the estimate is 20 (NL) and 21 (LEAN) whole problems, from 13 each.
- **Not yet shown:**
  - the count through `kit_fresh.py` with this solver as `--solver`;
  - that the known false proofs (IMO 2011 P6 and the controls in `PREREG_SIDE.md`) are still rejected;
  - whether figures near the proof's own figure test the proof as well as distant ones.
  These are task 1's registered run.
- **Distance check (job 1397601, same 41 statements):** the walk's accepted figures sit closer to the proof's figure than the default solver's. The median shape distance is 0.30 against 0.73 (points 0 and 1 fixed; the largest point move). That is still far beyond the 7e-5 near-coincidence behind the false IMO 2011 P6 proof. But task 1 should spread its figures as far as the default's: larger steps, or chaining from the farthest accepted figure, with the distance reported. That false proof is stored in the older AG format, which the kit can't read, so task 1 also needs a planted false proof in the decl format as its soundness control.
- The probe script stays outside the repository (`nlp_data/geo/kit_fresh_probe/`), so the method is the teammate's to write.

**2026-11-08 11:5x UTC: MechGeo's 44 IMO problems, final (SIDE-GT-MG): 13 whole problems with or without the audited Lean statement.**
- **MG-P2:** whole problems (faithful, proved, certified, 8 of 8 fresh figures): **NL 13, LEAN 13** (predicted 9 and 15; both in range). Faithful or half: 15 each. MechGeo without a human: 29 of 43.
- **MG-P3 fails:** LEAN − NL = 0 [−0.09, +0.09] per problem. So at IMO level the translator's reading is not what limits us.
- **Where problems are lost:** 15 of 44 have no statement that passes the guard, 5–6 no faithful one, 3 lose at the prover, 8 only at the fresh-figure rule (the solver built fewer than 8 new figures; none failed). Without that rule: NL 20, LEAN 21.
- **Cost:** 79k translator output tokens and 495 CPU seconds of closure per problem (NL, mean), against MechGeo's two hours per problem with two frontier models. Only cost is claimed; MechGeo's proofs are kernel-checked on the full statement.
- **Two LEAN rows have no closure result:** the child process exited silently (cause unknown; neither is a counted row).
- **For the teammate:** spend effort on (1) what one statement can't say: multi-part claims, case selection, and the 15 unexpressed problems; (2) the figure solver, which loses 8 faithful proved problems by building too few fresh figures. Feeding the model better hypotheses (the audited statement) bought nothing.

**2026-11-08 08:5x UTC: MechGeo's 44 IMO problems, translation stage (SIDE-GT-MG): the audited Lean statement does not raise the guard count.**
- **MG-P1:** problems with at least one guarded statement (four samples, two repair rounds, Qwen3.6-27B-AWQ): **NL 29 of 44** (predicted 20, range 12–26, so above), **LEAN 29** (predicted 28). 25 problems are guarded in both arms, 4 in NL only, 4 in LEAN only.
- Last-round status of the 176 samples: NL guarded 86, unexpressible 44, goal fails 23, no figure 17, syntax error 6; LEAN guarded 93, unexpressible 33, no figure 28, goal fails 21. Mean output 19.8k tokens per sample (NL), 15.3k (LEAN).
- The first job lost half its samples to client timeouts; the refill (job 1353077) completed all 176 per arm.
- **Next, as registered:** verdicts (faithful, half, changed, wrong) against the audited Lean statements, written before any closure run; then MG-P2 and MG-P3.
- **Verdicts before proof:** a faithful statement for 23 problems (NL) and 24 (LEAN); faithful or half 25 and 27. The translator's IMO-level faults: one goal per statement, so an iff gives one direction; missing case selection (points that may swap, a ratio met by both homothety centres, convexity cut down); hypotheses that assume the goal. A checker fault (a line given by one repeated point made any goal pass) is fixed. Closure running (jobs 1354571, 1354572).
- **For the teammate:** the audited hypotheses add one faithful problem (24 vs 23), so at IMO level the translation fails less on reading and more on what one statement can say: multi-part claims and case selection. Check those two first when reading a translation.

**2026-11-07 19:4x UTC: half of HAGeo's counted rows no longer assume a figure reading.**
- **SIDE-GT-LEAN-LIFT final:** all four predictions hold. 333 of 344 lifted certificates compile at 1,200 s; 126 of 263 counted rows have no reading (from 48); 11 faithful held-out problems (from 2), 8 once unsigned angles count as readings; no wrong constant. Lifting is now the default export.
- **Counts restated:** all 263 counted HAGeo rows are kernel-checked, 348 of 350 theorems compile, IMO-AG-30 27 of 27.
- **SIDE-GT-H409-RAND final:** random points 226, greedy 263, +37 [+23, +51]. The greedy stands.

**2026-11-07 14:5x UTC: readings can be proved, not assumed. First two theorems without them compile; no figure broke a reading on a counted statement.**
- **SIDE-GT-LEAN-RD:** of 273 readings on the held-out certificates, 271 have no figure where they fail. The other 2 are on ISL 2016 with a, b, p collinear, which the NDG stage already removed; the repaired rows have no failing figure. RD-P1 is far below prediction (0.7% against 35%), so `rctl` (SIDE-GT-LEAN-RC, job 1348742) now tests whether the search could have found one.
- **SIDE-GT-LEAN-LIFT (registered):** a row holds modulo π. Doubled rows and some rules (similar triangles, isosceles, midpoint, radius) hold modulo 2π, and a reading is exactly a relation modulo 2π, so proving one is integer linear algebra. `side/lean/GeoLift.lean` proves the rules. On the held-out export 220 readings are proved, 53 are left, 46 of 82 theorems have none (15 before), and no constant comes out wrong. Two ISL 2012 theorems compile with no reading. The full compile is running.
- **What blocks the 53:** order of points on a line or a circle (`coll` and chord rows), and side-side-side pairs with no angle relation at all.

**2026-11-07 13:3x UTC: 340 of 350 proofs pass Lean's kernel; a counted row now means a kernel-checked theorem.**
- **Result (SIDE-GT-LEAN):** 79 of 84 held-out and 261 of 266 HAGeo-409 certificates compile, with only Lean's standard axioms and no `sorry`, median 22 s. Two rest on a constant read from the figure and 8 ran out the 1,200 s limit (rerun with 4 hours). **No step was rejected**, so the Python checker's trust held on these sets, against my prediction that a gap would appear.
- **Counts:** held out **22 problems (16 whole, 6 parts)**, down one, because a part rests on a figure constant. HAGeo-409: 259 of 263 rows kernel-checked, 4 pending.
- **What these theorems assume:** distinct names, non-collinearity conditions and readings, all written in the theorem. **Only 3 of the 22 problems and 48 of the 259 rows are free of readings**, so these are not yet theorems about the statement alone. That is the gap. SIDE-GT-LEAN-NR looks for proofs without readings, and SIDE-GT-LEAN-RD asks whether a reading can fail on its statement.

**2026-11-07 11:5x UTC: the degenerate-figure stage reads, and every rule of the engine is now proved in Lean.**
- **SIDE-GT-NDG:** one counted problem has a real degenerate figure. On ISL 2016 the two lines that define P can coincide, leaving P free. The text excludes this by "the intersection point", so `ncoll a b p` is implied. All four statements reprove and pass the checker with it. **The count stays 23 (16 whole, 7 parts).** Coverage was 24% of triples, so this is a lower bound.
- **SIDE-GT-NDGP:** all 9 failing figures break a condition on the proof's list. Every condition was tested on 83% of certificates (90% needed), because circle tangency can't be written, so the list does not replace the triple search. 7 of 23 counted problems have an unstated condition with a figure; on 6 the goal still holds there.
- **SIDE-GT-LEAN (registered):** our "certified" rests on a Python checker that trusts each rule. `side/lean/` proves every rule on real coordinates in Lean 4 and Mathlib, with its conditions and figure readings as hypotheses. Next is one theorem per certificate. Prior work: an unfinished Newclid-to-Lean effort that named orientation as the hard part. MechGeo proves in Lean directly. No claim of a new idea.

**2026-11-07 10:0x UTC: REDU-E2 reads 6 of 6 after the fix; reduction becomes the default.** All six obligations are proved in one step and pass the checker, so every failure was the goal form (3 of 6 as registered). They are trivial duplicates, so this shows harmless redundancy costs no proofs, and no more. SIDE-GT-REDUCE-F, registered before any MechGeo translation exists, tests repair on statements nobody has read.

**2026-11-07 09:5x UTC: reduction puts USAMO 2006 P6's claim back among the goals, with no human.**
- **The fault it repairs:** all four translations assume three of the four circles concur, which is part of the claim, and agreement between translations can't see that.
- **Result:** the Jacobian test flags the assumed circle as implied by the rest. The closure proves it in 118 s, the checker passes it, and it holds on 8 of 8 fresh figures. With the original certified proof, "P on circles SAE and SBF" now gives both TCF and TDE, which is the problem. I read the proof: it is the textbook spiral similarity, and it uses the ratio. I gave this 40%.
- **Limits:** exploratory, on statements whose verdicts I had read, so it isn't a registered count. The proof holds for the configuration it read (3 readings) and needs 8 non-collinear triples. The existence of P, the second meeting point of two circles, is not proved.
- **REDU-E2 fails as registered, 3 of 6, on a fault of ours:** the closure raised an error on three-point circle goals, which are trivial here. Six obligations rerun with the goal written as equal lengths (job 1347198). If all pass, reduction becomes the default and the next test is a fresh set; if any fails, E2 stands as failed.

**2026-11-07 08:3x UTC: conditions read from the proof reach the failure the triple search found.**
- **Why:** the triple search (SIDE-GT-NDG) tries about 115 triples per statement and finished only 8 of its first 48 statements inside 600 s. A proof already lists what it needs: each rule holds only away from a degenerate figure.
- **Built:** `conditions` in `geo_check.py` reads those conditions from a certificate, and `pcond` in `geo_decl.py` tests each one. Median list: 13 conditions, 0 to 225. Registered as SIDE-GT-NDGP. It is the area method's bookkeeping moved to our rules, so I claim a tool and a measurement, not a new idea.
- **First reading of NDGP-P1:** all 9 failing figures so far, all on ISL 2016 (four samples), break a condition on the proof's list: `a b p`, and `a c i_a'` and `b c i_b'` on the same figures. Only that one problem has failures so far, so this is a small test. At a tolerance of 1e-6 four figures seemed to escape; that was the stored coordinates' rounding to 5 decimals, and at 1e-4 and 1e-3 none does.
- **Next:** job 1346805 tests every condition on all 84 certificates.

**2026-11-07 06:1x UTC: the closest prior work, found late, changes the next steps.**
- **MechGeo (2608.02295)** autoformalizes and proves IMO geometry in Lean: 29 of 43 without a human, all 44 with experts repairing 14 statements. It uses frontier models and two hours per problem, and Lean checks everything. Read in full, recorded in \`docs/notes/RELATED_WORK.md\`.
- **A threat to our counts.** It refuted 22 of 157 statements experts had called faithful, mostly on degenerate figures. Our figure solver keeps generic figures only, so we can't see this. SIDE-GT-NDG searches for such figures. The 23 counted held-out problems stay provisional until it reads.
- **A better reference.** Its 44 audited statements test our pipeline against something other than my reading: SIDE-GT-MG runs the full pipeline, and a second arm given the audited statement separates translator from prover.

**2026-11-07 02:3x UTC: two registered results.**
- **SIDE-GT-DECL:** end to end on the held-out 65, **23 problems (16 whole, 7 parts) against 17 (12, 5)** with the construction language, as predicted (+6). Six whole problems are new. The declarative form becomes the pipeline's language. These counts rest on my reading: agreement can't replace it here, so the no-human count of 13 stays with the construction language only.
- **SIDE-GT-H409:** **261 of 409** certified, by band 140, 84, 28, 7, 2 of 161, 112, 71, 43, 22. HAGeo reports 263 at K = 2,048 and 287 at K = 8,192, random points 218, AG1 177. Median 1.8 s per proved problem, 1,800 s limit on one core.
- **The checker found two faults in our code on HAGeo-409:** an unsound equal-chords step (four proofs; the same fault as the false IMO 2011 P6 proof) and a certificate export that corrupted large integers (three proofs). Both fixed; 264 of 264 now pass. Two rows lost their proofs and prove again on the fixed engine, reported apart: 263 with them.
- **Next:** by the registered rule, the same engine with uniformly random points, to measure what the greedy adds. The hard gap stays faithfulness without a human: REDUCE's obligations come next.

**2026-11-06 23:1x UTC: two faults found.**
- **Agreement fails on the declarative language.** It passes 5 of 7 unfaithful statements and all 25 half ones. All four translations of USAMO 2006 P6 assume three circles concur, which is the claim. Agreement therefore can't support a no-human count here.
- **The engine has a soundness fault, and the checker catches it.** On HAGeo-409 so far, 252 of 259 certificates pass. Four rejections accept equal chords on a premise whose constant is 1/2, not 0, as in the false IMO 2011 P6 proof. The fix waits for the running jobs.
- **Interim count:** 257 of 374 finished rows are proved with all fresh figures, before the checker (HAGeo at K = 2,048: 263 of 409). Not the registered reading.

**2026-11-06 21:5x UTC: declarative translations on the held-out 65, with verdicts before any proof.** Problems with a faithful whole-claim translation rise from 14 to 20, and with parts counted from 19 to 27. **A correction: 5 of the earlier 19 "faithful" problems were one direction or one part, so the reported 17 of 65 end to end means 12 whole problems and 5 parts.** Half statements are now counted apart. Proofs and agreement on these statements are running.

**2026-11-06 17:0x UTC: restarts decided; the search goes to HAGeo-409.**
- **SIDE-GT-LUBY:** 47 of 59 rows against 43, all passing the checker. It proves CAMO 2020 P3 with no random pool and loses nothing, so restarts become the default. It is 2.9 times slower on rows both prove (limit 2). The certified counts do not change, because that problem was already in the union.
- **Checker fault fixed:** its merge of collinear triples stopped too early, so three proofs failed wrongly. All sets were rechecked, with no other change: 241 of 242 proofs pass, and the false IMO 2011 P6 proof stays rejected.
- **SIDE-GT-H409, registered and queued:** the same search on the 409 problems of HAGeo's benchmark, counting only certified proofs. HAGeo reports 287, random points 218, AG1 177. I predict 234, range 190–280.

**2026-11-06 16:4x UTC: a correction, after reading the prior work properly.** 27 of IMO-AG-30 is not state of the art: AG2 and TongGeometry report 30, HAGeo 28, and random points in HAGeo's engine 25. So that count says little about the greedy. HAGeo-409 (409 problems, public) is the benchmark to report on next. What may be new is the independent checker and the end-to-end pipeline with an open model. The agreement check has a precedent (Li et al., 2410.20936). See `docs/notes/RELATED_WORK.md`.

**2026-11-06 15:0x UTC: the independent checker passes 150 of 151 proofs and rejects the false one. Certified: 27 of IMO-AG-30, 17 of 65 held out (13 with no human).**
- **The control worked:** the false IMO 2011 P6 proof fails on exact arithmetic. Its combination proves two lines perpendicular, and the proof uses them as parallel. The figure could not show this, because a point nearly coincided with another.
- **Four other proofs failed first on a fault in the checker,** which is fixed: it looked up a chord premise under the wrong name.
- **My prediction on configuration was wrong:** 91% of proofs read a configuration from the figure, mostly in similar triangles (predicted at most half). Those proofs hold for the figure's configuration only. 7 of the 27 and 3 of the 17 have a proof free of it.
- **The earlier counts were rechecked too:** their 44 rows were rerun through the closure, and all pass. Totals: 194 of 195 proofs pass.
- **Not checked:** non-degeneracy, the construction facts from Newclid's language, and about 20 classical lemmas stated in the checker's code.
- **Next:** the translator is the limit now. Restarts (SIDE-GT-LUBY) run on the last rows of the search, and declarative translations (SIDE-GT-DECL) wait for GPUs.

**2026-11-06 13:3x UTC: the greedy finds IMO 2008 P1b and 2019 P2 alone; 27 of IMO-AG-30 if the checker passes them.**
- **SIDE-GT-SQ:** all predictions hold. IMO 2008 P1b takes 4 s and the circumcentre, IMO 2019 P2 28 s and two points. The false IMO 2011 P6 proof is gone, and all 43 proved rows hold on 8 of 8 fresh figures. Still unproved of IMO-AG-30: 2008 P6, 2011 P6, 2021 P3.
- **Step replay failed its bar:** 490 of 614 steps (79.8%, bar 80%), with only 2 of 21 proofs reproduced whole. Newclid mostly stops without reaching the step. So `geo_check.py`, an independent checker with exact fractions, now decides certification, and it is running on every proof (job 1338729).
- **SIDE-GT-LUBY, registered and running:** the greedy chain's run time is heavy-tailed, so it restarts on Luby's universal schedule with no hand-set cut-off. It has to recover USAMO 2012 P5 or CAMO 2020 P3, which only a random pool proves.

**2026-11-06 11:5x UTC: IMO 2020 P1 proved by the textbook's points; one false proof caught; squared lengths added (SIDE-GT-SQ, registered, running).**
- **IMO 2020 P1:** the greedy's two points are the known solution's X and Y, in 16 s. It then proves DP = DX, that P, A, B, X, Y are concyclic, and that the bisectors at D and C are perpendicular bisectors of PX and PY. Not counted until replayed.
- **IMO 2011 P6 is a false proof, caught by the fresh figures:** a reflection fell 7e-5 from an existing point in the one figure, so facts about that near-coincident pair passed the numeric test and gained 71 relations. No step set held on any of the 8 fresh figures. Maximising gain selects such accidents, so a candidate's gain now counts on a second figure too.
- **Squared lengths as a third linear system:** ab ⟂ cd holds exactly when ac² − ad² − bc² + bd² = 0, an identity with no branch or orientation. With the circumcentre given, IMO 2008 P1b follows in 0.02 s from six such identities and two midlines. The engine could not reach it before, because it had nothing additive.
- **Candidate language:** it had no second intersections. Given the known solution's two, IMO 2019 P2 is proved in one round. Both kinds are now candidates.
- **The score drifts:** on all 8 rows that timed out, gain rises round by round, because relations among new points grow on their own. So the greedy wanders from the goal. This is the open search gap.

**2026-11-06 10:4x UTC: strict counts, and a point choice that takes seconds.**
- **Strict closure, decided (CLOSE-P6 holds):** 21 of the 29 problems no single point proved, 20 at a pool of 256 and IMO 2002 P2a at 64. No proof halves an angle, and every step holds on 8 of 8 fresh figures. So the halved angles cost almost nothing. **Correction:** I reported 23 of 31 earlier, counting some problems under two ids; the right figures are 21 of 29.
- **Counts if the certificate holds:** IMO-AG-30 24 of 30, held out 17 of 65 end to end, out of 19 faithful. Plain Newclid reproduces only 3 of 21 within 600 s, and the step replay's first run was unusable for similar triangles because of my replay; it is rerunning with that fixed (job 1337470). Three proofs are read by hand at the level of key lemmas (IMO 2000 P6, 2016 P1, 2018 P1). Not a claim until the replay is read.
- **SIDE-GT-SAT, registered and running:** no fixed pool. Each round scores candidate points by how many relations they add beyond the two closures apart, and the best becomes a point, so later points can build on earlier ones. On 8 problems already proved it finds proofs with 1 to 10 points in 2.5 to 82 s (IMO 2018 P1: two reflections, 2.7 s). The test is the 8 problems still unproved.

**2026-11-06 09:5x UTC: the translator is now the limit, so statements no longer need a construction order (SIDE-GT-DECL, registered, dev queued).** Half of the 260 held-out translations came back UNEXPRESSIBLE, because AlphaGeometry's language builds each point from earlier ones. The closure needs only a figure and facts. `geo_decl.py` takes points, hypotheses and a goal, and finds figures by least squares from random starts. A hand-written IMO 2007 P2, which the constructive language has no way to write, is proved by the strict closure with 5 points; that is my own translation and is not counted. A control I wrote shows a limit: a statement true only for a point inside the triangle is proved from facts that also hold outside, because a similar-triangles step reads its orientation from the figure, as Newclid's and AlphaGeometry's sameclock test does. So proofs hold for the figure's configuration.

**2026-11-06 08:4x UTC: most proofs halved an angle, so the closure now has a strict arm; the pool of 64 keeps 10 of its 11 problems.** Directed angles live modulo π, so 2a = 2b gives a = b or a = b + π/2, and the first engine, working over the rationals, picked the branch from the figure. 37 of the 44 proofs at K = 256 contain such a fraction. Fresh figures can't catch this, because they test the conclusion and not the deduction.
- **Strict arm (`GT_STRICT=1`):** an exact integer lattice with torsion runs beside the rational span. A premise or goal must be an integer combination of earlier relations, so no branch comes from the figure. Tested against brute-force enumeration on 12,000 small cases with no mismatch.
- **K = 64:** 10 problems, against 11 without the restriction, and no proof has a fractional angle coefficient. The loss is ISL 2016_23, an incentre problem, where a real branch was expected. So most of the fractions were an artefact of the log, which kept only relations independent over the rationals.
- **A false start:** my first version skipped relations like 2(a − b) = 0 and fell to 2 problems. That measured the shortcut, and I replaced it (recorded in `PREREG_SIDE.md`).
- **Plain Newclid (CLOSE-P4), 42 of 44 rows so far:** it reproduces only 3 problems within 600 s. The prediction of at least half looks refuted, so the step replay and hand reading carry the check.
- **Running:** strict K = 256 (job 1336308), the count that decides (CLOSE-P6), and the step replay (job 1335430). Still not a claim.

**2026-11-06 06:3x UTC: SIDE-GT-CLOSE, first full arms: 23 of the 31 problems no single point proved. Not yet a claim.** All candidates in one closure, same candidate generator as the random arms:
- Pool of 0: 4 problems. Pool of 64 (the exact pool the random arms searched): 11, in about 0.6 s per translation. Pool of 256: 23, in 53 s per translation. Pooling and pairs together proved 2 at 8,000–9,600 s.
- I predicted 12 (7–18) for 256, so this is above my range, which by the project's rule makes it a suspected bug until read. So far: every step of all 44 proofs holds on 8 of 8 fresh figures, and I read one proof by hand, IMO 2000 P6's row, at the level of its key steps. Its key lemma, that triangle x2 y2 t2 is similar to t1 t3 i because reflections double an angle, is a real argument.
- Still open: plain guarded Newclid on the same points (job 1334911), the arm with every candidate (job 1334653), and how much fractional chases matter.
- If this stands, the proof step stops being the bottleneck: 10 of the 12 faithful held-out problems that remained unproved fall here, which would make 17 of 65 end to end out of 19 faithful, and the translator becomes the limit.

**2026-11-06 06:2x UTC: guarded counts decided, pooling withdrawn, and a new engine that may replace the search over points.**
- **Counts under the guard (SOUND-P1 holds):** held out 8 of 65 (4 by DDAR alone, 3 with one point, 1 by pooling), IMO-AG-30 13 of 30. No proof uses a false statement.
- **Pooling (POOL-P1 holds as written, on one problem):** it proves Indonesia 2007 P7, but that is one point missed once by a time limit, not facts adding up. Its one real composition, USAMO 2005 P3, fails its certificate. The 64 random pairs prove IMO 2010 P2 in one translation. I withdraw pooling and the planned ordering of candidates: there is no data to order by.
- **A correction:** HAGeo's repository holds only a README and figures; the code awaits review.
- **SIDE-GT-CLOSE, pre-registered.** DDAR is monotone, so one closure over a whole pool contains every proof using any subset of it. The obstacle is speed. `geo_closure.py` computes what is true on the figure first, then tests each true instance's premises, with angle and length chasing as a constant-time test of membership in a linear span. It reproduces 42 of 44 recorded proofs in about 0.01 s each; with no construction facts it proves none. On a timing test of 5 rows, a pool of 256 points proved IMO 2018 P1 and ISL 2012 (opc_IMOSL_2012_19) in about 35 s, against no proof from 131 DDAR calls per translation by pooling. **These are not claims yet.** Full runs and hand reading come first, and fractional chases pick a branch from the figure.

**2026-11-05 21:2x UTC: third rerun, one auxiliary point: 7 of 65 held out, 13 of 30 references, and the audit is clean.** All 44 proofs (dev, held out and
references) were audited, with no false statement on their own figure or on 8 fresh figures, and no error. 43 reran within 120 s; USAMO 2010 P1 (DDAR alone) did not.
- Held out: 4 by DDAR alone (Pan African 2002, Romanian NMO 2006, USAMO 2010 P1, ISL 2012_16) and 3 with one point (Pan African 2004, USAMO 2008 P2,
  ISL 2012_18). The withdrawn count was 10.
- IMO-AG-30: 10 by DDAR alone and 3 with one point (IMO 2004 P1, 2012 P1, 2014 P4). The withdrawn count was 14.
- **IMO 2000 P1's gap (2026-11-05 22:0x UTC: resolved, the count stays 13).** Its goal comes through `cong e p e q` with no recorded reason, on all 6 seeds that finished, and one run's
  written proof has no steps at all. Newclid's congruence lookup returns no reason when two segments already share a length symbol. A trace of that merge shows a
  real rule application: EQ = EP by r10, from `eqratio e q p c e p p c`. So the step exists and the written proof loses it. The proof text is incomplete, and its statements
  are all true.
- Pooling and pairs are still running, so SOUND-P1 and POOL-P1 to P3 are not yet decided.

**2026-11-05 20:1x UTC: plain Newclid, re-audited with the fixed test: 10 of 54.** The recorded proofs that reran under plain Newclid use a false statement
in 10 of 54 cases, not the 16 of 57 first reported. SOUND-FIX-P3 (at most 13) holds.
19 of 68 rows still raise an error. So the finding stands at its corrected size: plain Newclid can derive false facts and they spread.

**2026-11-05 19:1x UTC: a second fault in the same test; a third rerun.** My fix kept Newclid's rule that a line is not parallel to itself, but Newclid also
writes `para c p c k` to say that c, p, k are collinear. The fixed test therefore rejected those true facts, and the plain re-audit flagged them
(27 of 56). Now `para` only compares directions. In a guarded sample, 2 of tens of thousands of checks are rejected, both false by far more
than rounding. Everything reruns in `results/proof/sound3/`. The second rerun's first stage gave the same counts, 7 of 65 and 12 of 30, with two problems
changed in the references.

**2026-11-05 17:0x UTC: the guard and the audit had a fault; the pipeline reruns again.** The audit of those 43 proofs: all reran with no error, and I read
the flagged statements. All are `para` or `perp`, and all are true (sine or cosine at most 1e-10). Newclid tests these two against an absolute
1e-12 on an unnormalized product, which my tolerance setting did not reach.
- So the flags were false alarms, and the guard rejected some true facts (9 of 219 in a quick sample). The 7 of 65 and 12 of 30 below are
  lower bounds, and the earlier "16 of 57" is overstated: 3 of the 16 are flagged only on these two predicates.
- The fix tests both on the normalized angle. Everything reruns in `results/proof/sound2/`, and SOUND-P1 and pooling are decided there.
- Still to read by hand: IMO 2000 P1, whose proof has one statement (`cong p e q e`) with no reason given.

**2026-11-05 16:5x UTC: one auxiliary point under the guard: 7 of 65 held out, 12 of 30 references (not yet audited).** Same 64 random points per
translation, at 60 s, now with every derived fact checked on the run's figure.
- Held out, faithful translations: 3 problems by DDAR alone (as before) plus 4 with one point (Pan African 2004, USAMO 2008 P2, USAMO 2010
  P1, ISL 2012_18). That is 7 against the recorded 10, within the 5–8 registered. Lost: CAMO 2020 P3, ISL 2016_23, ISL 2017_19.
- IMO-AG-30 references: 9 by DDAR alone plus 3 with one point (IMO 2004 P1, 2013 P4, 2014 P4). That is 12 against the recorded 14, the
  bottom of the 12–14 registered. Lost: IMO 2010 P2, 2018 P1.
- A lost proof is not yet known to have been false: runs have a random order, so a rerun is not the same run.
- Next: the audit of these 43 proofs (job 1329373) decides SOUND-P1. Pooling and pairs are still running.

**2026-11-05 14:5x UTC: DDAR alone survives the guard.** Rerun with `GT_SOUND=1` at 60 s, then read against the earlier run. The audit of these proofs
is still to come.
- Dev: the same 7 translations and 4 problems (IMO 2010 P4, 2014 P4, 2015 P4, 2017 P4).
- Held out: the same 8 translations and 5 problems, of which the same 3 count as faithful (Pan African 2002, Romanian NMO 2006,
  ISL 2012_16).
- Translations whose DDAR run raised an error: 21 → 3 on the held-out set, 5 → 0 on dev.
- So the loss is expected in the auxiliary-point results, whose rerun is running. The withdrawn counts stay withdrawn until it finishes.

**2026-11-05 14:4x UTC: Newclid's proofs are not exact (SIDE-GT-SOUND).** While reading an early proof of ISL 2004 G8, I found CE = DE given as
a premise and AB ∥ CD derived from it, and neither holds in general. Newclid 2.0.2 checks the goal numerically and has an option, off by
default, to check an added statement, so a false fact can spread and "prove" a true goal.
- **Audit** of 68 recorded proofs (`geo_translate.py audit`), every statement tested on its own figure at 1e-4: with plain Newclid, 57
  reran, 16 use a false statement, and 20 rows raised errors. With the guard (`GT_SOUND=1`, every derived fact and merge must hold on the
  run's figure), 47 reran, none uses a false statement, and no row raised an error.
- **Withdrawn until the rerun finishes:** 10 of 65 held-out problems with one auxiliary point, 8 of 65 with no human in the loop, the four
  shortlist problems, and IMO-AG-30's 14 of 30.
- **Still to read:** IMO 2000 P1's proof uses `cong e q p e` with no reason given, though it holds on all 8 fresh figures. A few statements
  fail on some fresh figures where the goal holds, which may be another intersection point.
- Newclid 3.0.1 exists and has not been tried. HAGeo (2512.00097) also has an appendix on a fallacious AlphaGeometry proof of IMO 2020 P1.

**2026-11-05 11:5x UTC: pooling facts across auxiliary points (SIDE-GT-POOL, registered).** Each point runs alone, and every fact it proves about
the figure's own points goes into a pool, fed back as lemmas with no point added. That is k + 1 runs instead of k²/2 pairs. AlphaGeometry2's
SKEST shares facts between trained-model search trees, with no ablation and no run without a language model, so the measurement here is
what sharing adds on its own, with random points. Two faulty runs were stopped, as recorded in the prereg. No verdict yet.

## Proofs (`side/proof_falsify.py`, `side/geo_translate.py`; section C in older records)

**What the main track already knows** (`docs/prereg/PREREG_PROOF.md`):
- Lean 4 (miniF2F): the compiler is a perfect check.
  - A specialised 8B prover beats general models (Goedel-Prover-V2-8B 180 of 244 statements, Qwen3.6-35B 133).
  - Hints in the prompt and repair from compiler errors do not help.
  - Many cheap attempts before thinking is the right budget split, and 30 graded statements find it.
- When to stop trying on a statement, from Lean's feedback, is published (2606.04883: −26% compute at matched accuracy), so it is not
  a side project here.

**The gap:** natural-language proofs, where nothing checks a proof for free.
- In the Open Proof Corpus (OPC, 2506.21621; 4,934 proofs by frontier models, graded by humans), the judges' feedback on wrong proofs
  names:
  - a missing justification in 22%;
  - a wrong final answer in 15%;
  - a false claim or a counterexample in 10%;
  - no solution in 5%;
  - nothing at all in 51%.
- Computation can catch only the wrong answers and the false claims.

**Tried on proofs (SIDE-PF dev, 11-04):** a model writes one program per proof that brute-forces the answer on small cases and tests
the proof's concrete claims; a printed counterexample flags the proof.
- On 60 OPC proofs it flagged wrong and right proofs alike: 11 of 30 wrong vs 9 of 30 right (Qwen3-8B, no thinking); 6 vs 5 with
  thinking.
- The false flags come from testing something the proof does not claim: "infinitely many n" tested at one n, values outside the
  hypotheses. Rerunning code cannot fix that, so the proof-level check is dropped.

**A statement alone, before any proof (dev, 11-04; BrokenMath, competition statements perturbed to be false):** reasoning already
separates them.
- Qwen3-8B with thinking, asked "true or false", flags 97% of false statements and 17% of true ones.
- A counterexample program flags 79% and 23%. Requiring both cuts true-statement flags to 7%, at 12.7k tokens.
- Translated to Lean by Qwen3-8B, 67 of 78 statements do not even compile, and Plausible cannot sample ℝ. Not pursued.

**Geometry proofs checked numerically (SIDE-PG dev, 11-04): no recall.** The program drew random instances of the figure and checked
the proof's concrete claims, discarding instances where the problem's own (true) conclusion failed.
- On 57 OPC geometry proofs it flagged 0 of 38 wrong and 0 of 19 right proofs with thinking (12.7k tokens; a third hit the 16k cap).
- The judges name a false geometric fact in only 6 of the 38 wrong proofs; the rest are gaps or missing work, which no numerical
  test sees. Frontier models' proofs of OPC's 22 shortlist geometry problems are right in 2 of 105 cases.

**Geometry by translation and a symbolic engine (SIDE-GT, `side/geo_translate.py`).** The model writes no proof. It
translates the statement into AlphaGeometry's construction language, and Newclid's DDAR (Sicca et al., 2411.11938; CPU) proves it.
- The free check: the problem's conclusion must hold numerically on a random figure built from the translation's hypotheses alone.
  A false goal holds on none; a translation that adds a hypothesis still passes, so faithfulness is read by hand or against a
  reference translation.
- What is known: proving from the construction language is close to solved without a network (HAGeo, 2512.00097: 28 of 30
  IMO-AG-30 on CPU). Translation is the weak link: open models reach at most 46% executable translations even with 54 examples
  (NL2AGBench, 2608.28481). Untested: a small model with this guard and resampling.
- Data: `$POC_DATA/geo/problems.jsonl`, 89 problems (OPC's 22 shortlist geometry problems and 67 from theblackcat102/IMO-geometry),
  11 with an IMO-AG-30 reference; 24 for development, 65 held out.
- Setup: `pip install --no-deps --target $POC_DATA/geo/pylib newclid==2.0.2 colorama networkx pyvis seaborn`; run the check with
  `PYTHONPATH=$POC_DATA/geo/pylib`.
- What we built on top of the guard:
  - repair turns that show the model Newclid's error;
  - `--grammar`: the final line is decoded under an EBNF of Newclid's 81 constructions and their argument counts, using vLLM 0.22's
    `structured_outputs.grammar`;
  - a trivial-goal test that rejects a goal already among the construction's facts;
  - retries on other diagrams when Newclid fails on one (`GT_DDAR_SEEDS`);
  - `aux`, a search over one auxiliary point at a time.
- Results (FINDINGS 11-04; PREREG_SIDE SIDE-GT-H):
  - **Qwen3-8B:** fails as the translator. 1 of 24 dev problems is translated faithfully. The grammar removes the syntax errors,
    but what then passes is trivially true.
  - **Qwen3.6-27B-AWQ** (two 3090s, thinking at medium effort, k = 4, grammar, 2 repair turns):
    - dev: 6 of 24 problems faithful; DDAR proves IMO 2010 P4, 2014 P4, 2015 P4 and 2017 P4;
    - held out (faithfulness judged before any proof attempt): 19 of 65 problems faithful (29%), but DDAR alone proves only 3
      (4.6%; the registered bar of 5 was missed). One of the 3 is ISL 2012 G (2012_16), where frontier natural-language proofs are
      right 0 of 8 times.
  - **gpt-oss-120b:** declines 78 of 96 dev translations as unexpressible. It is faithful on 4 problems, and DDAR proves 1.
- **Correction (11-05, SIDE-GT-SOUND):** counts of proofs here assumed DDAR's proofs were exact; see the log. Run with `GT_SOUND=1`, and audit
  proofs with `geo_translate.py audit`.
- **No human in the loop (SIDE-GT-AGREE):** agreement between independent translations replaces hand reading. On a figure built from one
  translation, the other's construction predicates and goal must hold, both ways. Of 59 translations with blind verdicts, it accepted
  no unfaithful one (0 of 6) and 47 of 53 faithful ones. This check is numerical, so the correction above does not touch it.
- **Auxiliary points from the model (SIDE-GT-AUXP):** Qwen3.6-27B's proposed points proved nothing random points missed, though they found a
  point in fewer tries (695 DDAR calls against 3,514). That was measured with plain Newclid, so it needs rereading under the guard.
- So with a 27B translator the prover is the bottleneck. A project for algorithms work: auxiliary constructions when DDAR stops.
  Our first search is uniform over construction type, then over arguments. HAGeo's heuristics (28 of 30 on IMO-AG-30, random
  constructions 25) are the published target; their code is at github.com/boduan1/HAGeo.

**Other hard proofs, the same question** (OPC graded proofs, wrong / right): is there a free check that sees the common error?

| Area | Free check | OPC (wrong / right) |
|---|---|---|
| Inequalities | numerical minimisation refutes a false step; an SOS certificate proves a polynomial one (LIPS, 2502.13834) | 101 / 93 |
| Functional equations | plug in the claimed solutions; search simple families for missed ones | 190 / 89 |
| Combinatorics | brute force on small cases: the claimed extremum, the claimed construction | 188 / 109 |

None of these sees a step left unjustified while true, the most common error (85% of solutions in IneqMath), so a symbolic engine
that proves, as in geometry, is the stronger route where one exists.

## Constructions: the computation side of proofs (`side/construct.py`; section D in older records)

**Why:** the side work on math runs two ways (user, 11-04): proofs (geometry, above) and computation. A constructive problem
("show that an object with these properties exists") is proved by the object, and whether an object is right is decided by computing.

**Data:** MathConstruct (Balunović et al., 2502.10197; eth-sri/mathconstruct, MIT): 121 competition problems, each with a
human-written verifier and a generator of variations (other parameters, so a remembered answer does not help). Published: o3-mini
(high) 65% of variations; models writing brute-force code 5–10%, and 11–19% when they search small cases and generalise (2024 models,
without thinking). `side/construct.py build` writes two variations of each problem (226 instances of 115 problems; 40 problems for
development, 75 held out).

**Questions:**
1. Which route gives a verified object with the fewest tokens: answer directly (quick or thinking), or write a program that builds or
   searches for the object.
2. Can a checker the model writes from the statement alone, before seeing any answer, stand in for the human verifier as the free
   check? On these problems its false accepts and false rejects are measured exactly. Related: ComBench (2606.10479) has a model
   write verifiers to build a benchmark, then audits them; we found no test-time use.

**Setup:** MathConstruct needs `sympy`, `antlr4-python3-runtime==4.11`, `pydantic`, `loguru`; grading runs with
`PYTHONPATH=$POC_DATA/construct/mathconstruct/src`.

**Results (Qwen3-8B; PREREG_SIDE SIDE-MC-H, 147 held-out instances):**
- One thinking answer with a 30k cap solves 23.1% (22.2k tokens); a 16k cap cuts most runs off (dev: 9 vs 18 right).
- A thinking program solves 18.4%, mostly different instances: the two are right on 27 and 34, only 13 in common.
- The model's own quick checker is not a usable free check. It rejects 28% of right objects, so the registered cascade
  (program, checker, then the answer) is not significantly better than the answer alone (+4.8 points [−0.7, +10.3]).
- Taking the program's object whenever it parses, else the answer, gains +6.8 points [+0.7, +13.5] at 1.4× the tokens. That was
  a secondary arm; it needs a fresh test before anyone relies on it.
- Open question for the teammate: a checker that is right more often than the model's own (written once per problem and checked
  on small cases), or a search program that the problem's structure makes exact.

**For algorithms work:** the program route is search (backtracking, SAT encodings, local search), and "search small cases, find the
pattern, build the large case" is a method of its own.

## Earlier second-track work (no longer the side project)

These two components were built before the side project became proofs. They stay as examples of the interface and as records of what was
tried. Pick either up only as a new proposal.

### Generated agent environments (`side/envs/`, `side/gen_*.py`)

**What for:** the multi-turn methods (a verifier choosing among sandboxed turn rollouts) are trained and tested on BFCL v4's 8
environments. A new environment family with algorithmic ground truth is a test no verifier has seen.

**What a family is:**
1. **A class.** Methods are the tools, the state lives in public attributes, `_load_scenario(config)` loads the state, and errors are
   returned as `{"error": ...}`. See `envs/package_manager.py`.
   - A result must depend only on the call and the state before it. Never put counters or call order in a result.
2. **A generator.** It writes BFCL-format items: `id`, `cat`, `system` (BFCL's header plus the function docs), `turns`,
   `initial_config`, `involved_classes`, `ground_truth`.
   - The ground truth of a turn is computed by an algorithm, such as a resolver, a search or a shortest plan, under a policy the
     function docs state.
   - The end state must be unique under that policy. BFCL grades by the end state plus an unordered check of the results.
   - Each request must state the rule it implies (which dependencies, which version, what to clean up), as BFCL's requests do. The
     first version of the package manager left two conventions to the function docs, and no model followed them, thinking or not:
     2.5% right (`PREREG_SIDE.md`, SIDE-ENV results).
   - Keep every request kind at no more than a third of the turns. In the second version (rules stated), half of the turns were
     removals with clean-up, and those capped whole conversations at 17.5% with thinking (SIDE-ENV-2).
   - See `gen_pkg.py` and `gen_cal.py`.

**What a family must show** (from three tries: SIDE-ENV, -2, -3):
- Thinking pays. It did in both families, by +15 to +50 points.
- Qwen3-8B with thinking is right in at least 20% of conversations. Both families missed this: 17.5% (packages) and 15% (calendar,
  one booking, one move and one cancellation per conversation).
  - A conversation is right only if every turn is: with a per-turn right rate q, k turns give about q^k. In the calendar, thinking
    got 14 of 28 bookings, 16 of 21 moves and 8 of 23 cancellations right (each counted until the conversation's first wrong
    turn), so three turns land near 0.5 × 0.76 × 0.35 ≈ 13%.
  - Choose the number of turns and the request kinds from a small pilot's q, so that q^k for Qwen3-8B with thinking falls in
    [20%, 85%].
- An error in a turn tells a right turn from a wrong one no better than on BFCL. Otherwise a check that escalates on errors would
  already do the verifier's job.
  - Measure the error rate of right turns against wrong turns, up to each conversation's first wrong turn (`analyze_env.py`
    prints it), and pre-register it that way.
  - BFCL's anchor (turn 0, `results/conf/mt_sel_rows.jsonl`): Qwen3-8B's quick turns show an error in 33% of right turns and 75%
    of wrong ones; with thinking, 29% and 57%.
  - In the calendar it was 9 of 9 right turns and 35 of 40 wrong ones (quick), because the model guesses ids and room names in the
    same step as the reads. That is less separation than BFCL's. SIDE-ENV-3 counted the share of failures without an error instead,
    a measure that fails a family where errors are everywhere.
3. **The CPU check**, which must pass before any model runs:
   `python side/check_env.py <items.jsonl> <Class=side.envs.module> --negative '<a correct fragment>' '<a mistake>'`.
   - The ground truth must be valid for every item.
   - A deliberate mistake must make most items invalid.

**Ideas for the next families:** each should have real constraints and a policy with one answer. The package manager and the
team calendar (`envs/team_calendar.py`) are closed as test beds, and they are examples of the interface.
- Bank transfers under daily limits and fees: the cheapest valid sequence.
- A warehouse: picking under capacity, shortest route.

Add a "missing parameter" variant: a turn that lacks a needed value has an empty ground truth, and the next turn supplies the value, as
in BFCL's `multi_turn_miss_param`.

**The main track runs** `poc/run_mt.py` and `poc/grade_mt.py` unchanged, with
`MT_CLASSES=<Class>=side.envs.<module> MT_ITEMS=<items>`. Then `python side/analyze_env.py <Class=side.envs.module> <items.jsonl>
<tag>` gives the registered numbers for any family: right and tokens per arm, thinking minus quick with its interval, and, for each
failed conversation, the first turn where its state leaves the ground truth's, which attributes differ there, and whether that turn
showed an error.

### Distinguishing sub-databases for SQL (`poc/sql_witness.py`; closed)

**What it was for:** when two candidate SQL queries return different rows, a trained pairwise verifier picks one. A witness shows the
verifier why the two queries differ: a few rows of the real database on which they still disagree.

**What it does:** delta debugging over rows, with foreign keys closed and the results' shape kept as on the real database. It finds a
witness for 98.4% of the target pairs, with a median of 3 rows.

**Result (SIDE-W, 11-04):** the verifier trained with witnesses equals the one without, in every test set. The witnesses are right and
readable, but the 8B verifier does not use them: its choice changes less than retraining alone changes it. Side project B is closed.
The code stays as an example of a delta-debugging component.
