# Pre-registration X7: the final recipe on a held-out benchmark (MAMO), with no hand-written fact

Written 2026-10-19 02:37 UTC, before any run. Results go below.

**Why.** Everything so far was developed on NL4OPT / IndustryOR and our generated suites. MAMO (Huang et al. 2024; EasyLP 652 + ComplexLP 211
optimization word problems, CardinalOperations/MAMO) has not been used. The recipe as it now stands, with no human-written component:
the fact = the model's own shortest program from NL4OPT / IndustryOR that passed the label-free check (runs and prints a value); write
the program with it (twice); think only unless both run and agree (FFR) — or only if it fails to run (FF). The hand-written snippet is
run alongside as the reference. Models: Qwen3-32B-AWQ (GPU0), Qwen3-14B-AWQ (GPU1), gpt-oss-20b (GPU2; low effort for the cheap
arms, medium for thinking), Qwen3-8B (GPU3, expected to lag); tag <model>_mamo (poc/queues/queue_s2_x7.sh).
Arms: mip s1 (no fact); mipf s1–2 + thinkf s1 (hand-written); mips s1–2 + thinks s1 (automatic).
- X7-P1: automatic FFR within 2 points of hand-written FFR for Qwen3-32B, Qwen3-14B-AWQ and gpt-oss-20b; ≥ 4 points below for Qwen3-8B.
- X7-P2: automatic FF ≥ always-thinks − 2 points at ≤ 40% of its tokens for those three models.
- X7-P3: picking the policy (CHEAP / FF / FFR / THINK) from 30 labelled MAMO items gives ≤ 1.5 points of regret (λ = 0.5) per model.
