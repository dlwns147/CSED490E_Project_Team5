# Pre-registration L1: does helper steering survive when the helpers are an importable library described only by its API?

Written 2026-10-13 23:29 UTC, before any run below. Results are appended below without editing this section.

**Why (Limitation 1, synthetic contexts).** In F1 the helpers are pasted as source code that the model may copy. Real assistants more often
see a library's API reference (signatures + one-line docs) and import it. If the steering needs visible code, the practical warning is narrower.
**Design.** Qwen3-8B and Qwen3-32B-AWQ, no thinking, `--stdlib`, T = 0.7, seeds 1–2, the 5 core tasks (300 programs per seed), the same
helper draws as F1 (K0 = needed helpers only, K8 = + 8 related extras). New: `--tb_api`: the prompt says "The Python module `geomlib` is
installed; import what you need from it" followed by the API list (signature + its one-line comment, no code); at execution the module
exists with exactly those functions. References on this stack: the copy-in K0 / K8 runs (C1).
**Predictions.**
- L1-P1: the API-only toolbox still harms: K8-API − K0-API ≤ −5 points for both models.
- L1-P2: the harm is smaller than with copy-in code: |K8-API − K0-API| < |K8 − K0| (copy-in) for both models.
- L1-P3: hull carries the harm: hull under K8-API ≤ 50% correct for both models.


---
## Results (appended 2026-10-13 23:33 UTC; predictions above unedited)

Correct on all 8 variants, 2 seeds × 300 programs; paired 95% CI. 599 of 600 K8-API programs import from `geomlib`.

| model | copy-in K0 → K8 | **API-only K0 → K8** | hull: copy-in K0 / K8 | hull: API K0 / K8 | hull API-K8 programs using `polar_sort` |
|---|---|---|---|---|---|
| Qwen3-8B | 552 → 468 (−14.0) | 469 → 463 (−1.0 [−4.3, +2.3]) | 109 / 23 | **13** / 42 | 91 / 120 |
| Qwen3-32B | 551 → 451 (−16.7) | 558 → 442 (**−19.3** [−23.2, −15.5]) | 100 / 25 | 104 / 32 | 84 / 120 |

- **L1-P3 confirmed:** with only an API list, hull still collapses under 8 extras (35% / 27%), and 70–76% of hull programs import the
  offered `polar_sort`: the steering does not need visible code.
- **L1-P1 split:** 32B loses 19.3 points (as much as with copy-in code); 8B shows no K8 effect (−1.0) only because its K0 baseline already
  collapses: read from the failures, the 8B **imports library functions that do not exist** — `from geomlib import convex_hull` in 53 of
  54 failed hull programs at K0 (the API lists only `orient`), `polygon_area` in area2 — so its programs die with ImportError.
- **L1-P2 split:** smaller harm for 8B (for the reason above), not for 32B.
- Reading: a library framing keeps the algorithm steering (32B) and adds a new failure, hallucinated API (8B assumes the library already
  solves the task). Neither depends on helper code being pasted into the prompt.

---
## Extension L2 (registered 2026-10-14 00:28 UTC, before running): does stating "these are the only functions" stop the hallucinated imports?

Same API-only conditions (K0, K8; seeds 1–2; Qwen3-8B and Qwen3-32B) with one added sentence after the API list: "The module contains
exactly these functions and nothing else; anything else you need, write yourself."
- L2-P1: Qwen3-8B hull at K0 recovers from 13 to ≥ 90 of 120, and programs importing a function not in the list drop to ≤ 10 of 600 at K0.
- L2-P2: the steering harm remains for 32B: K8 − K0 ≤ −10 points with the sentence.


### Extension L2 results (appended 2026-10-14 00:33 UTC; predictions above unedited)

| model | API-only K0 / K8 (L1) | + "exactly these functions" K0 / K8 | hull K0 / K8 | programs importing a function the module lacks (K0 / K8) |
|---|---|---|---|---|
| Qwen3-8B | 469 / 463 | **553** / 500 (−8.8 [−12.2, −5.3]) | 13 / 42 → **103** / 46 | 106 / 64 → **3** / 20 |
| Qwen3-32B | 558 / 442 | 561 / 441 (−20.0 [−24.0, −16.2]) | 104 / 32 → 104 / 33 | 0 / 0 → 0 / 0 |

- **L2-P1 confirmed:** one sentence removes the hallucinated imports (8B: 106 → 3 programs at K0; hull 13 → 103 of 120), at no token cost.
- **L2-P2 confirmed:** the steering remains (32B −20.0; and with the hallucinations gone, 8B's own steering shows again: −8.8, hull 103 → 46,
  `polar_sort` imported in 92 of 120 hull programs). The sentence fixes the false belief about the library, not the algorithm choice.
