# Related work and baselines, per finding (checked 2026-10-13)

Four literature searches (one per theme), each opening the papers on arXiv / proceedings; earlier checks are in FINDINGS.md
("Deep related-work check for G2 and CO1", "Novelty check T1 / T2", "Related-work check for the toolbox/distractor theme").
Numbers quoted from papers came through a page reader: re-check before citing exact figures. "(search only)" = not opened.

## Verdict per finding

| finding | already known (cite) | what looks new in ours |
|---|---|---|
| F1 helper steering | Incidental prompt cues steer the algorithm family a model writes, by up to 100 points, even neutral cues (2606.04057, "The Invisible Lottery", 2026); an available but unneeded tool hurts without being called, fixed by a one-sentence scope instruction (2609.14157, NeurIPS 2026); over-trusting plausible agent skills (2608.11888); retrieved similar or buggy code context hurts code generation (2503.20589; 2306.03438, NeurIPS 2023); misleading hints and comments (CodeCrash 2504.14119, NeurIPS 2025); GSM-IC; tool overload (RAG-MCP, ToolRet) | correct-but-unneeded *code to copy* collapses correctness (hull 97 → 8%, not just style); per-token logit evidence of the route shift; dose-response in K; reasoning models immune; the input-format spill-over (E2) |
| F2 hidden contract | under-specified tool descriptions cause misuse and fuller descriptions repair only part (2602.14878, "MCP tool descriptions are smelly"); tool-doc refinement DRAFT (2410.08197, ICLR 2025); models rarely satisfy contracts, stating them helps little (ContractEval 2510.12047); docstring perturbation (2504.19108); API misuse taxonomy (2503.22821, TSE) | matched comparison of the same helper with vs. without the orientation dependence; the needed helper worse than no helper; 4 models, 2 families; warning recovers 16–75%; thinking fixes it at 32B but not 8B; no geometry-predicate study found |
| F3 solver API facts | OR-Tools VRP code with decomposed doc / example retrieval, irrelevant-document filter matters (**DRoC, ICLR 2025**); one-line API docs help CPMpy / MiniZinc but not OR-Tools, retrieved examples hurt (CP-Bench 2506.06052, ECAI 2025); compact API spec + selective retrieval (Jain et al. 2407.09726); high-ranked near-miss documents hurt (Power of Noise 2401.14887); EHOP 2502.13776 | exact 5-line snippet beats full manual *and* reasoning at matched cost; near-miss snippet = no doc; retrieval works only when top-1 is exact; strong models unhurt by extra chunks; 51% of CO failures are API knowledge |
| Format override (VRPTW field, count line) | reasoning models override explicit conditions with familiar patterns (2505.17225 "Reasoning model is stubborn"; Inverse Scaling in Test-Time Compute 2507.14417); redefined built-ins / constants get worse with scale (2305.15507; 2502.12821); inverse scaling prize (2306.09479); counterfactual tasks (2307.02477, Embers 2309.13638) | **Corrected 2026-10-13 (F3y):** our VRPTW case was an ambiguous header (`service horizon` read as one compound noun); with `service_time` the failure disappears (120b low 30/30). What remains ours: the diagnosis (counterfactual re-run; asking the model to restate the format), the literal-input fix, and the geometry count-line failure caused by irrelevant helpers. The planned scaling study is dropped |
| F4 MR-select | prompt-side metamorphic / paraphrase consistency for code (2406.06864; CCTEST 2208.08289; Chan et al. JSS 2025); program-agreement on new inputs (MBR-exec 2204.11454, CodeT 2207.10397, S* 2502.14382, incoherence 2507.00057 which also notes zero-incoherence errors); instance perturbation with provably valid relations for optimization models (2607.16646); Spatter 2410.12496 | selection by consistency of ONE program on transformed copies of the GIVEN instance (no new inputs, no labels), for geometry; best-of-3 beats thinking at ≈1/6 tokens on slips |
| C1 confidence | mean-logprob ranking helps Codex (2107.03374, opposite direction); likelihood favours degenerate / repetitive programs (Coder-Reviewer 2211.16490; 2206.02369); poor calibration of code LMs (2402.02047, ICSE 2025); token confidence AUC ≤ 0.70 and no reliable selection gain (2610.11300, Oct 2026) | head-to-head with the metamorphic check on the same samples; inversion under misleading helpers (AUROC 0.43, 32B: area2 0.33); anti-correlation on hard tasks |
| E3 / E3b routing and brute-force oracle | draft-agreement → think routing; many errors are agreeing wrong drafts (DART 2606.23181); test-gated cascades (2405.15842), AutoMix, FrugalGPT; compute-optimal allocation (Snell 2408.03314); brute-force oracles ALGO 2305.14591 (correct on 72–88%), ExeCRE 2608.04439; shared errors (2506.07962) | label-free check-gated routing loses to a fixed small thinking budget at matched tokens; brute-force reference catches 86–90% of invariant errors but costs as much as thinking and fails on lattice |
| F5 / E4 self-replay | own outputs forget less: on-policy data explains RL < SFT forgetting, with a mixed teacher-vs-own comparison (2510.18874, ICML 2026); self-distillation for continual learning (2601.19897); SDPO 2601.20802; own verified outputs damage other tasks less (2501.14315, NeurIPS 2025); SDFT 2402.13669; SSR 2403.01244; self-generated replay 2605.26097; RL's Razor 2509.04259; LoRA forgets less 2405.09673; style-induced drift 2602.20162; System-2 distillation 2407.06023 | the controlled same-prompt contrast (self 118 vs teacher 36 vs none 48 of 120), with the teacher being the same weights in thinking mode, and the idiom drift as visible mechanism. Present as a clean test of the on-policy explanation, not a new mechanism |
| E1 taxonomy | code-error taxonomies (2406.08731 ICSE 2025; 2407.06153; 2403.08937 EMSE 2025; 2411.01414; 2409.20550 ISSTA 2025); optimization-modelling errors (2510.16943); self-repair cost (2306.09896); paraphrase-only control for input edits (2605.01048, COLM 2026) | CG / CO domain, 14.8k failures, behavioural labels with counterfactual re-runs, class × fix map against a re-sampling control |

## Baselines worth running (priority order; all with open models via vLLM and our harness)

1. **Label-free selection vs MR-select (F4, C1, E3):** MBR-exec / incoherence clustering on generated inputs (github.com/facebookresearch/mbr-exec);
   CodeT dual agreement + B4 scoring (github.com/microsoft/CodeT, github.com/ZJU-CTAG/B4); self-certainty / DeepConf as the strong
   confidence selector (github.com/backprop07/Self-Certainty; needs top-k logprobs); DART-style router (two no-thinking drafts, agree →
   answer, else think) and a fixed thinking-budget sweep for E3. Cost: ≈ 0–1 extra generation per instance + execution.
2. **Forgetting mitigation vs self-replay (E4):** WiSE-FT-style LoRA scaling θ0 + α·BA (no training; github.com/mlfoundations/wise-ft);
   SDFT rewrite of teacher programs by the student (github.com/sail-sg/sdft prompts); KL-to-base on replay prompts (peft disable_adapter);
   self-SFT on the student's own verified programs; on-policy distillation (trl GKDTrainer). Cost: 1 LoRA run each (≈ 10–25 min).
3. **Helper context (F1, F2):** helper pruning by the model (we ran self-scoping before: precision-limited) and perplexity-based chunk
   ranking (LongCodeZip, github.com/YerbaPage/LongCodeZip); the one-sentence scope instruction (2609.14157) and System 2 Attention
   (2311.11829); DRAFT-style docstring rewriting by probing the helper (github.com/quchangle1/DRAFT) vs our hand-written warning.
4. **Solver code (F3, format):** done as B4 (docs/prereg/PREREG_B4.md): DRoC-style retrieval beats top-3 but not the exact snippet; restating fields does nothing. Originally: DRoC (github.com/Summer142857/DRoC; needs a vLLM + local-embedder port, ≈ 4–8 × cost); Self-Debug style
   repair (we already use 2 repair rounds); a µFiX-style "restate the input fields / predict the parse of an example" prompt vs our literal-stdin fix.
5. Lower priority: OptiMUS, Chain-of-Experts, ORLM (LP/MILP-oriented, OpenAI- or COPT-specific; heavy port to OR-Tools routing).

## Added 2026-10-14 06:42 UTC (hard-problem benchmarks)
- Contest geometry: AlphaCode (2203.07814) filter by public examples + cluster by behaviour (our H2b/H2c selection is this, at k ≤ 8);
  MBR-exec (Shi et al. 2022); arXiv 2506.22954 excludes figure-dependent geometry problems (we report that subset separately).
- Optimization at benchmark scale (for H3): HeuriGym (2506.07972; LLM-written heuristics, incl. pickup-and-delivery with time windows,
  low solve rates under constraints); AFL agentic VRP framework (2510.16701; within 3% of HGS on most VRP benchmarks); ARS (2502.15359;
  automatic routing solver with LLMs); VRP + LLM survey (2607.00604). Solomon best-known solutions use vehicles-then-distance
  (SINTEF), so a gap must state its objective.

## 2026-10-16: prior art found for "verify once, reuse" and for the N10-N12 line (abstract-level; read the full text before any claim)
- One solver per problem family, run on every instance: Distribution-Aware Programming with LLM agents (arXiv 2605.14141; writes
  specialised solvers from training instances, LLM only before deployment); "LLMs Can Design Near-Optimal OR Algorithms" (arXiv
  2608.27296; one query per problem family, the solver runs on every instance); RL to make a code LLM synthesise a reusable solver for
  a family (ChatPaper listing, May 2026, constrained quadratic knapsack); AutoSG (2605.25658) ranks generated solvers by LLM-judge Elo.
  -> Our V1 is not new as an idea; what remains ours: the measured per-instance vs reuse gap (7% vs 94%), the answer-free check +
  agreement tie-break, the cost rule (tokens per candidate / share working), facts raising the working share, size transfer.
- Correlated errors: SAGA (arXiv 2507.06920): LLM-induced errors are highly clustered, verifiers built from LLM data miss them;
  differential test-time scaling (2605.20473) uses agreement across candidates. Mixture-of-thought cascade (Yue et al., ICLR 2024)
  gates escalation on CoT vs program agreement. -> N12 (agreement across tool conditions) is a variant of these.
- Editing solvers when constraints change: ARS (2502.15359) regenerates heuristic code per VRP variant (RoutBench, 1,000 variants);
  DRoC (ICLR 2025) retrieves per constraint; constraint injection for LLM optimisation modelling (2606.04816) is the closest; no paper
  found that edits a verified solver and re-verifies it on the new variant.
- 2026-10-16 (read the abstract page): arXiv 2606.04816 "Beyond Objective Equivalence: Constraint Injection for LLM-Based Optimization
  Modeling on Vehicle Routing Problems" (Findings EMNLP 2026) is a VERIFIER, not code editing: solutions that violate exactly one
  constraint detect omitted constraints, feasible ones detect wrongly added constraints; used as rejection-sampling filter and RL reward
  (VRPCoder 8B, VRPBench 21 variants, 93% Pass@1). Relevant to our "check is the bottleneck" thesis (a label-free check of the
  constraint set, beyond feasibility of one output). Editing a verified solver under a rule change: still no prior work found.
