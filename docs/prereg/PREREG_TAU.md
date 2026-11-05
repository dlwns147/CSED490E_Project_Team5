# PREREG_TAU: choosing per turn when only the end of a conversation is scored (τ²-bench)

Written 2026-11-05 23:2x UTC, before any rollout or simulated-user comparison has run. Only the two pilot runs below had been read.

**Why.** MT-SO, the project's main result, picks among sandboxed candidate turns with a verifier trained on per-turn labels, which BFCL gives free. τ²-bench (retail, airline, telecom; simulated user; train and test splits) scores only the end of a conversation, so those labels do not exist. This is the hard gap: where do per-turn labels come from when the score is global?

**Pilot, Qwen3-8B as agent and as simulated user, train split, seed 1.** Retail: quick 12.2% of 74 at 1.0k tokens, thinking 26.7% of 30 at 8.8k. Airline and telecom are still running. Read raw: the simulated user often fails its own part. In task 30 it says none of its listed orders holds the tablet (invented), and in tasks 3 and 7 it repeats the same message for most of the conversation. Scores on this user are not comparable with published ones, and a label is only as good as the simulator behind it.

## 1. TAU-U: is the simulated user good enough to give labels?

**Design.** An agent given the gold resolution steps (τ²'s own `llm_agent_gt`, Qwen3-8B thinking) meets each simulated user on 30 train tasks per domain, seed 1. With the steps given, failures are mostly the user's. Users: U8 (Qwen3-8B quick, as in the pilot), U8t (Qwen3-8B thinking), U9 (Qwen3.5-9B quick), U36 (Qwen3.6-35B-A3B-FP8 quick). The user's tokens are the world's cost, not the agent's, so they are reported but not charged.

**Predictions.**
- **TAU-U-P1:** under U8 the agent with the gold steps is right on 40–65% of the 90 tasks.
- **TAU-U-P2:** the best other user beats U8 by +8 points, range +3 to +20, paired over tasks. With 90 tasks the half-width is near 10, so P2's decision below may well keep U8.

**Decision.** Use the user with the highest score among those whose paired 95% lower bound over U8 is above 0; if none, keep U8. Whichever is chosen, thinking is rerun under it where the pilot used another, as the base of TAU-R.

## 2. TAU-R: how much is there to gain, and the labels

**Method.** From a user message, each candidate turn runs in a sandbox and the base policy finishes the conversation. The end reward is a Monte Carlo sample of Q(state, candidate turn). This gives labels for every turn from a global score. The conversation is then played by the rollout algorithm: commit the turn whose rollout scored best, the base policy's on a tie (a tie is no evidence), take the user's reply and repeat (`poc/tau2_q.py`). Candidates: two thinking turns and two quick turns; thinking is the base. The peer's quick turn is added if a second server is already up for the chosen user.

**Theory.** With exact Q, the rollout policy is at least as good as its base (Tesauro and Galperin 1996; Bertsekas). The gain equals the sum of advantages along the new policy's path (performance difference lemma, Kakade and Langford 2002). Playing the policy measures that directly, without the first-order approximation of summing advantages along the base's path, and at about the same cost. The final reward of a played conversation is a real sample of the policy's value. This policy uses the simulated user and the score, so it is an upper bound and a label source, never a test-time method. A verifier trained on these labels would see neither: only the conversation and the candidate turns.

**Related work (one round of search; it does not settle it).** LATS (2310.04406) searches over actions with an untrained value score. MT-GRPO on τ-bench airline (2606.00135) gives per-turn credit to train the model, not to choose among turns at run time. I found no paper training a run-time turn verifier on continuation values.

**Bar, derived.** A later online test would use all 278 tasks (train and test, cross-fitted) at 3 seeds. Taking the per-task paired standard deviation as 0.45, its half-width is 1.96 × 0.45 / √278 = 5.3 points. On BFCL the verifier realised 56% of the oracle's gain. So the gain must be at least 5.3 / 0.56 = **9.5 points** for a verifier's gain to be visible. The standard deviation is re-estimated from the data here, and the bar recomputed by this formula.

**Predictions** (90 train tasks, 30 per domain; V_R is the rollout policy, V_T thinking on the same tasks and user).
- **TAU-R-P1 (decision):** V_R − V_T is +25 points, range +12 to +40, with a paired lower bound above 0.
- **TAU-R-P2 (reported):** the share of committed turns from the quick arm, and how V_R − V_T splits by domain.
- **TAU-R-P3 (reported):** the rollout policy's gain arises mostly before the conversation's first write action, because a wrong write is usually final: more than half of the turns that replace the base's come before it.

**Decision.** If P1 holds and the gain reaches the bar, train a cross-fitted verifier on the labels (Qwen3-8B LoRA, conditional logit over the candidate set, as MT-SO), pre-register its online test here, and run it. If the gain is below the bar, per-turn choice has no visible room on τ²: stop, and report that its reach is limited to benchmarks where a turn's own quality decides. The result is reported in either case.
