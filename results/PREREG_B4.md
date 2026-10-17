# Pre-registration B4: published retrieval / spec-reading methods vs the exact API snippet and the literal input (F3)

Written 2026-10-13 19:29 UTC, before any data below. Results are appended below without editing this section.

**B4a: DRoC-style decomposed retrieval (ICLR 2025) vs the exact snippet.** A constraint-level OR-Tools routing documentation base is
written once, before any run, in the style of the official routing guide: 12 titled chunks (model setup and arc costs; capacity
dimension; time windows with a time dimension; service times; search parameters; reading routes; and 6 plausible near-misses:
optional visits / disjunctions, pickup and delivery, multiple depots, depot resource limits, vehicle fixed costs, global span cost).
Arms (solver arm, repair 2, T = 0.7, seeds 1–2, CVRP and VRPTW, 30 instances each): (i) **exact snippet** (our F3 fix); (ii) **BM25 top-3**
over the library with the problem text as query; (iii) **DRoC-style**: the model lists the constraints the problem needs, BM25 top-1
per constraint, the model filters the retrieved chunks for relevance, then writes the program with the kept chunks.
Models: Qwen3-32B-AWQ and Llama-3.3-70B (no thinking).
- B4-P1: DRoC-style ≥ BM25 top-3 (both models, pooled CVRP + VRPTW), and ≤ the exact snippet.
- B4-P2: DRoC-style costs ≥ 2 × the exact-snippet arm's generation tokens per instance (decomposition + filtering + longer prompt).

**B4b: restating the input fields (spec-restating / µFiX-style prompt) vs showing the literal input.** VRPTW with the exact snippet,
gpt-oss-20b and gpt-oss-120b at low effort, seeds 1–2: the prompt adds "Before writing the program, list the fields of the stdin format
in order (one per line, with their meaning), then write the program." References on this stack: prose only 120b 0/30, 20b .07–.17 (old);
literal stdin 120b .97–1.00, 20b .80–.90.
- B4-P3: restating recovers less than half of the literal-input gain for gpt-oss-120b low (opt rate < .50).
- B4-P4: restating reduces the programs that skip the `service` field, but less than the literal input does (counterfactual check).


---
## Results (appended 2026-10-13 19:56 UTC; predictions above unedited)

`poc/analyze_b4.py`. The documentation base was checked before any run: a program assembled only from its 6 needed chunks is optimal on
5/5 VRPTW instances.

**B4a (opt rate, 2 seeds × 30 instances; tokens per instance incl. decomposition / filtering / repairs):**

| model | problem | exact snippet | BM25 top-3 | DRoC-style | DRoC − BM25 | DRoC − snippet |
|---|---|---|---|---|---|---|
| Qwen3-32B | CVRP | .77 @ 1.7k | .48 @ 2.3k | .72 @ 2.1k | +.23 | −.05 |
| Qwen3-32B | VRPTW | .23 @ 3.1k | .02 @ 3.8k | .03 @ 3.8k | +.02 | −.20 |
| Llama-70B | CVRP | .92 @ 0.7k | .35 @ 1.9k | .72 @ 0.9k | +.37 | −.20 |
| Llama-70B | VRPTW | .63 @ 1.6k | .10 @ 2.4k | .03 @ 2.8k | −.07 | −.60 |
| pooled | both | .50 / .78 | .25 / .23 | .38 / .38 | +.12 [+.03, +.22] / +.15 [+.05, +.24] | −.12 [−.23, −.03] / −.40 [−.50, −.30] |

- **B4-P1 confirmed:** DRoC-style decomposition + filtering beats plain top-3 retrieval (+.12 / +.15 pooled; the filter drops the
  near-misses: e.g. on CVRP 32B retrieves "depots" in 56/60 and keeps it in 0) but stays below the exact snippet, far below on VRPTW.
- **B4-P2 not confirmed:** DRoC costs 1.2–1.6 × the snippet's tokens, not ≥ 2 ×, because repair rounds dominate every arm.
- Why DRoC fails on VRPTW although it retrieves and keeps exactly the right chunks (time windows, service, capacity, setup, routes in
  55–60 of 60): the models splice patterns across chunks. Llama passes the capacity chunk's per-vehicle list to the time dimension
  (`routing.AddDimension(time_idx, 0, [horizon] * num_vehicles, False, "Time")`, TypeError in 44/60) and sets the waiting slack to 0;
  Qwen3-32B builds `RoutingIndexManager(num_locations, K, [0] * K)` (23/60). The exact snippet shows the calls already assembled for this
  problem, which is what the models need.

**B4b (VRPTW, exact snippet, gpt-oss low, 2 seeds × 30):** restating the fields first: 120b 0/30 and 0/30 (programs skipping `service`
29, 26); 20b 2/30 and 2/30 (19, 20), at 5.1–5.6k tokens. Literal stdin: 120b 29/30, 29/30; 20b 27/30, 27/30.
- **B4-P3 confirmed** (restating recovers nothing), **B4-P4 not confirmed** (it does not even reduce skipping).
- **And it exposed the cause:** asked to restate, gpt-oss-120b writes "`n capacity K horizon` … maximum route end time (service horizon)":
  it reads our header `n capacity K service horizon` as four fields with the compound noun "service horizon". Follow-up F3y
  (FINDINGS, pre-registered): with the header written `n capacity K service_time horizon`, 120b low is 30/30 and 30/30, 20b low 29/30
  and 29/30, with no program skipping the field. The skipped-field failure was an ambiguity in our format string.
