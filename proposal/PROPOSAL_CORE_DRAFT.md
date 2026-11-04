# Draft core for the proposal (experiment session, 2026-10-16 18:25 UTC; not yet in PROPOSAL.md)

Purpose: replace the "catalogue of fixes" reading with one claim, why it matters, and the test that can falsify it.

## Title
**Compute cannot buy what the model does not know or cannot see: three failure mechanisms of LLM-written programs, their signatures,
and what to spend instead**

## The problem and why it matters
- LLMs increasingly *compute* answers by writing programs (route planners, schedulers, geometry and math code), and the dominant way to
  make them more reliable is to spend more test-time compute: more samples, longer reasoning (up to 30k tokens per problem), chosen by
  how *difficult* a prompt looks (Snell et al., ICLR 2025).
- Our measurements say this misallocates compute for a large class of failures:
  - **Missing knowledge.** Qwen3-32B writing OR-Tools code: reasoning longer .03 optimal, a 5-line exact API fact .77–.90; the fact
    even makes programs shorter. No amount of compute supplies a fact the model does not have.
  - **Context steering.** With unneeded helper functions in the prompt, convex hull drops from 97% to 8%; the model is *confident*
    (it calls the misleading helper with higher token probability than the needed one) and *consistent* (samples agree), so every
    check built from the same model (self-consistency, symmetry tests, "pass the examples") accepts the error.
  - **Leaky checks.** Cheap checks never reject a correct program but accept 24–37% of wrong contest programs, and they leak more as
    the model gets stronger: the verifier blind spot that recent work finds across model families (Kim et al. 2025; Goel et al. 2025;
    Rajput et al. 2026) appears *within* one model as soon as its errors become systematic.
- These matter beyond our tasks: they decide whether an agent's code is silently wrong, and how much a deployment pays per answer.

## Central claim (testable)
Failures of LLM-written programs come from three mechanisms with label-free signatures, each needing a different resource:
| Mechanism | Signature (no answer key needed) | What fixes it | What does not |
|---|---|---|---|
| missing knowledge | low token confidence at the API / library name; samples disagree | the exact fact (≈ 200 input tokens) | more reasoning, more samples, full manuals |
| context steering | high confidence; samples agree; changes when the tool condition changes | a second opinion with independent errors (same model, tool removed); reasoning only when they disagree | resampling, self-consistency, same-condition checks |
| reasoning difficulty | samples and models disagree; checks leak | more reasoning, gated by a decorrelated check (brute force) | facts, tool changes |
Plus one structural lever: when the same problem repeats, compute is paid once (one verified program reused: routing 7% → 94%,
job-shop with a new rule 12 → 82–120 of 120 by adapting the verified program).

## What is new
Difficulty-based allocation, uncertainty-triggered retrieval and verifier blind spots exist separately. New here: (1) the
*confident-and-consistent* steering class, invisible to every sample-based uncertainty signal and every same-model check, and its
detection by changing the tool condition; (2) allocating three different resources (facts, decorrelated checks, reasoning) by the
measured signature, priced in tokens; (3) measured on tasks with exact answers (geometry, routing, scheduling, contest geometry,
competition math).

## The decisive tests (pre-registered)
- U1 (PREREG_U1.md): do the signatures separate the mechanisms, and does allocating by mechanism beat allocating by difficulty at
  equal tokens? If not, the claim is wrong.
- X1 (PREREG_X1.md): does a decorrelated second opinion (text vs program) gate reasoning on competition math, beyond computation?
- X2 (PREREG_X2.md): does "verify once, reuse" carry over to math word problems with numeric variants?
