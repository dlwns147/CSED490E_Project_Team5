# How much do the cheap checks miss? (compiled 2026-10-16 16:32 UTC from stored runs; results/checks_coverage.log)

Answer to "isn't it solved by verifying the output?": every check below has **no false alarms** on the runs measured (a correct program
never fails it), but each **accepts a large share of the wrong programs**, and the share grows as the model gets stronger.

| Domain / check | What it verifies | Wrong programs it accepts | Source |
|---|---|---|---|
| Contest geometry: the statement's examples (1–3 inputs) | the examples' outputs | gpt-oss-120b low 122 / 503 (24%), medium 151 / 403 (37%), high 106 / 315 (34%); Qwen3.6 142 / 536 (26%) | 311 problems × 3 seeds |
| Generated geometry: symmetry check (shifted / rotated / mirrored copies agree) | consistency, not correctness | Qwen3-32B with the K8 toolbox: 9 / 37, 18 / 50, 12 / 46 per seed (24–36%) | N10 |
| Optimization, solver programs: feasibility of the printed plan | the constraints, not optimality | Qwen3-32B free choice 6 / 178 (3%), gpt-oss-120b 11 / 55 (20%; median gap 5.7%) | N15 |
| Optimization, plain-Python programs: feasibility | the constraints, not optimality | Qwen3-32B 142 / 234 (61%, median gap 15%); gpt-oss-120b 114 / 145 (79%, gap 8%) | N15 |
| Job-shop, plain-Python programs: feasibility | the constraints | gpt-oss-120b 77 of its 80 feasible plans are > 5% from the best (median 200%) | N15e |

Second opinions that catch part of what the cheap check accepts (contest, gpt-oss-120b medium, wrong example-passers):
| Second opinion | Catches | False alarms | Extra cost | Source |
|---|---|---|---|---|
| approximate brute-force oracle on small generated inputs | 42 / 86 (49%) | 30 / 403 (7.4%) | 2.9k tokens / problem (197 of 311 problems get one) | N13 |
| a second model's example-passing program (Qwen3.6) on the same inputs | 21 / 51 (41%) | 29 / 329 (8.8%) | 3.4k tokens of a 3B-active model | N17 |
| a second tool condition (geometry: with vs without helpers; escalate on disagreement) | all but 1 of 37–50 wrong first attempts per seed | escalates 37–53% of items | a second cheap program (0.4k) + thinking when escalated | N12 |
| a second tool condition on contest (gpt-oss-120b low with vs without the K8 toolbox) | 28 / 66 (42%) | 11 / 317 (3.5%) | a second low program (3.2k) | N19 (helper-immune model: both conditions share their mistakes) |
| the model's own token log-probs (Qwen3.6, lowest token log-prob of the program) | AUROC 0.69 wrong-vs-correct among example-passers (mean 0.61); choosing by confidence among 3 samples +1.3 points | – | free (stored with the generation) | N18 |
| comparing objectives across solver libraries (optimization) | picks the optimal plan in 64–93% of instances (vs 41–82% for one library) | – | ≈ 4 × tokens (cascade: 1.4–3.7k) | N15d / N15f |

Reading: verification is easy where the property is a constraint (feasibility) and the program uses a solver (wrong solver programs
mostly crash or print infeasible plans); it is weak where correctness means "the right number" (geometry, contest) or "the best plan"
(heuristics). A check never fixes a program either: when no candidate is right (Qwen3-32B job-shop: 4 of 80), checking only
rejects. Hence the project's two kinds of fixes: give the fact up front (prevention), or add a *different* second opinion
(detection) and pay for the expensive fix only when it disagrees.
