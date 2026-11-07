# Ideas for the computation track

The user asked on 2026-11-07 for ideas from many angles, tested as they come, with no method fixed for now. Each idea gets the cheapest test that could kill it. Results go in `docs/FINDINGS.md`. A pilot here decides nothing; anything that survives gets a pre-registration and a read of its closest prior work in full.

The gap all of these aim at: on AIME, Qwen3-8B gets about 12% from a quick answer and 63–68% from thinking at 16k tokens, and agreement checks accept only what quick answers already get right.

| # | Aspect | Idea | Nearest work (depth read) | Cheapest test | State |
|---|---|---|---|---|---|
| 1 | Check | **Lean as the check on an answer:** state "the answer is x" as a theorem, let the compiler decide | Don't Trust: Verify, ICLR 2024 (abstract only) | Accept rate and false accepts on dev against "two text answers agree" | Next; read DTV first |
| 2 | Check | **Clean number:** an output that looks exact is likely right | PSLQ practice in experimental mathematics; no use on LLM answers found | Recorded program outputs | **Failed** |
| 3 | Check | **Check the answer, not the solution:** the model writes a verifier by substitution or a certificate (feasible point and dual bound for optimization) | Not yet searched | One prompt on AIME and MATH level 5 | **Failed** as a filter at 8B; FAIL is a clean reject. OptiBench dual bounds untested |
| 4 | Check | **Brute force beside the fast program:** random small cases compared | ALGO-style oracles (from memory, unchecked) | Contest code set | Open |
| 5 | Decorrelation | **Which pairs share mistakes:** family, mode | Partially Correlated Verifier Cascades, 2607.13918 (abstract, introduction) | Recorded runs | **Measured:** family matters most |
| 6 | Budget | **Agreement-gated early exit:** stop thinking when the running answer matches an independent cheap answer | Answer Convergence 2506.02536, PUMA 2605.17672, DEER (snippets) | Raw traces, job 1349138, then offline | **Running** |
| 7 | Budget | **Restart a long think** | short-chain preference (from memory, unchecked) | Recorded seeds | **Failed** |
| 8 | Budget | **Think to verify:** give the thinker a candidate and a small budget | Not yet searched | Quick answers then capped verification | **Running** |
| 9 | Exactness | **Small cases and extrapolation:** brute force small parameters, fit a recurrence or polynomial | Not yet searched | AIME and MATH level 5 | **Failed** as a replacement; adds 11 of 180 new right AIME runs |
| 10 | Exactness | **Numeric, then identify:** high-precision value, then a closed form | mpmath identify; no LLM use found | AIME and MATH level 5 | **Failed** |
| 11 | Amortization | **One think, many instances:** a parametric program paid once over a family | Metacognitive Reuse 2509.13237, CC-LEARN 2506.15662 (snippets) | Templated sets (MAMO, optimization) | Open |
| 12 | Amortization | **A growing library of checked programs** over a stream of problems | Extends our missing-fact result | Ordered stream on recorded problems | Open |
| 13 | Tools | **Tool calls inside thinking:** exact steps replace long hand arithmetic | Tool-integrated reasoning work, unread | Tokens at equal accuracy, Qwen3-8B | Open |
| 14 | New problems | **Tasks with exact validators:** planning (PDDL), scheduling, spreadsheet tables | Not yet searched | One benchmark with a free validator | Open |
| 15 | Theory | **When does a second check pay,** given error correlation and price | 2607.13918 is theory on synthetic data | Derive, then fit idea 5's table | Open |
