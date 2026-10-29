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

## Search 2026-10-19 (2026-10-19 07:28 UTC): optimization modeling, automatic facts, when-to-think — closest work and how we differ
- **OptiSkill** (arXiv 2609.22987): a hierarchical SkillBank (global formulation strategies + step-level error rules) distilled from a strong
  teacher's (DouBao-Seed-2.0-Pro) Gurobi programs on 1K OptMATH problems, **validated against ground-truth answers**, routed to 8
  problem-type sub-banks; frontier backbones reach MAMO Easy / Complex 90.8–94.3 / 56.8–64.0%, IndustryOR 71–74%. Closest to our mined
  facts. Differences: ours are the *same small model's* programs selected by a **label-free** check (runs and prints), no teacher, no answers;
  we show *why* type routing is needed (a mined fact from another problem type carries the wrong library / backend: −14 to −21 points)
  and combine the fact with check-gated thinking. Their type routing is consistent with our cross-type failure.
- **EVOM, execution-verified RL for optimization modeling** (2604.00442), **OR-R1** (2511.09092), **Step-Opt** (2506.17637), **CALM / STORM**
  (2510.04204: STORM-Qwen3-4B MAMO 86.3 / 70.3%), **ORLM** (2405.17743: LLaMA-3-8B, reported MAMO 82.3 / 37.4%, NL4OPT 85.7%, IndustryOR 38.0%):
  training-based. Our recipe is training-free; on MAMO it puts untrained 3090-class models at ORLM-8B's level (Qwen3-8B 81.7 / 37.9%,
  Qwen3-14B-AWQ 82.8 / 37.4%; gpt-oss-20b 85.6 / 57.8%), below a trained reasoning 4B (STORM) and frontier agents (OptiSkill). Grading
  conventions differ across papers (MAMO labels are noisy; reported ORLM numbers vary 81.6–88.2% Easy); a same-harness ORLM run is queued.
- **OptArgus** (2605.11738, multi-agent hallucination detection in optimization modeling), **localizable error-driven modeling** (2602.11164):
  checks / repair for formulation errors — related to our check-leak finding (better facts → fewer crashes → more wrong-but-running programs).
- **API documentation for code hallucination** (Amazon CloudAPIBench, 2407.09726): documentation helps rare APIs, hurts frequent ones with a weak
  retriever; selective retrieval by index check or confidence (+8.2 points). Matches our N16 (log-prob trigger) and our name-list failure.
- **When to think**: Thinkless (2505.13379, NeurIPS 2025) and AdaptThink (2505.13417) *train* a mode switch (RL); "What if we allocate
  test-time compute adaptively?" (2602.01070, ICML 2026) allocates with a process reward model; none use an execution check after giving a
  fact, and none compare with difficulty-based allocation (Snell et al.) at matched tokens as we do.

## Related-work check for the 2026-10-23/24 results (literature search, 2026-10-24)
**1. Fact first, think on failure — known idea, new angle.** Cheap-first escalation on a failed check is established for *cascades
between models*: answer consistency (LLM Cascades with Mixture of Thought Representations, ICLR 2024, 2310.03094), self-verification
(AutoMix, NeurIPS 2024, 2310.12963), self-generated tests (Model Cascading for Code, 2405.15842). Deciding *when to think* inside one
hybrid model is mostly learned (AdaptThink 2505.13417, Thinkless 2505.13379, AutoThink 2505.10832; OptimalThinkingBench, ICLR 2026,
2508.13141: no model thinks the right amount). The accuracy ceiling from false positives of an imperfect check is predicted by The Limits
of Inference Scaling Through Resampling (ICLR 2026, 2411.17501). Retrieval of facts / similar solved problems: DocPrompting (ICLR 2023);
for OR modeling MIRROR (2602.03318), 2608.00015. Reasoning models sometimes below non-reasoning ones on NL4OPT / MAMO / IndustryOR:
OR-LLM-Agent (2503.10009). **New here:** the fact-matched comparison (thinking given the same fact), the per-model split (pure saving vs
trade) explained exactly by the false-pass decomposition, and the evidence on OR / geometry; the 30-label pilot is standard cascade tuning.
**2. Proofs: cheap attempts before thinking — mostly established.** Reasoning Models Can Be Effective Without Thinking (2504.09858):
no-thinking matches thinking on MiniF2F / ProofNet at every k with 3.3–3.7× fewer tokens; DeepSeek-Prover-V2 non-CoT vs CoT (2504.21801);
repeated sampling with a perfect verifier: Large Language Monkeys (2407.21787). Only modestly new: "thinking adds statements only after
cheap sampling saturates" on general hybrid models.
**3. Label-free fine-tuning — mostly established.** Self-consistency-filtered self-training (LLMs Can Self-Improve, EMNLP 2023,
2210.11610; STaR; ReST-EM); training on usage beats docs in context (CodeUpdateArena 2407.06249); context distillation (2209.15189).
Collapse under self-agreement rewards: Can Large Reasoning Models Self-Train? (2505.21444), Co-rewarding (ICLR 2026, 2508.00410),
sharpening / self-improvement gap (ICLR 2025, 2412.01951, 2412.02674); cross-model agreement: Co-rewarding, Multiagent Finetuning (ICLR
2025, 2501.05707). Expert iteration on Lean Workbook: Polu et al. 2022, DeepSeek-Prover, Goedel-Prover (2502.07640), STP (ICML 2025,
2502.00212; plain expert iteration plateaus). **New here:** program-level agreement on OR problems as the filter, and the negative data
point that a cross-model filter removes harm but adds nothing. DT-P (Lean expert iteration) was withdrawn before results for this reason.
**Open questions not answered by prior work:** (i) a few-label predictor of when escalation pays (false-pass rate, cheap pass rate,
thinking's accuracy on failures); (ii) label-free checks for OR programs that turn the Qwen3 trade into a pure saving (problem-semantic
metamorphic relations, thinking-mode review of the cheap program); (iii) thinking-vs-non-thinking mode agreement as a self-training filter.

## Related-work check 2026-10-27 (2026-10-27 13:32 UTC): thinking budgets (HO-SB / SB4 / PB / 4K / SEED / CM), tool calling (TC-1), instruction following (IF-1)

**Budgets and the short think first.**
- Budget forcing: s1 (2501.19393, EMNLP 2025; AIME24 50 → 56.7 by forcing; budgets written into the prompt fail because the model cannot
  count). Most of s1's scaling is scaling down, and tight caps lower the ceiling (Wu, 2507.14419).
- What a cut does: Qwen3's report (2505.09388) inserts "Considering the limited time by the user, …" at the budget, an untrained, emergent
  behaviour. Nemotron Nano 2 (2508.14444): an untrained cut makes the model reason on in the answer, fixed by training on traces cut to
  1–2k tokens; Nemotron-3-Nano (2512.20848) truncates 3% of its fine-tuning traces. Seed-OSS has budget-reflection tags but no published
  adherence data. → HO-SEED (overrun in 88–99%, answer-side reasoning to the 8k cap) is new as a measurement.
- Trained length control: L1 / LCPO (2503.04697), Elastic Reasoning (2505.05315, separate think / answer budgets), TALE (2412.18547),
  ThinkPrune (2504.01296), AnytimeReasoner (2505.13438), BudgetThinker (2508.17196), SelfBudgeter (2505.11274), AlphaOne (2505.24863).
  Early exit from inside the think: DEER (2504.15895), ThinkBrake (2510.00546), FlashThink (2505.13949), probes (2504.05419), answer
  convergence (2506.02536) — none uses an execution check.
- Longer is not monotone: overthinking (2412.21187), underthinking (2501.18585), an inverted U in length (2502.07266), non-monotone gains
  and parallel beating extended thinking (2506.04210, NeurIPS 2025), inverse scaling (2507.14417), abandoned right answers (2604.10739),
  3–19% of items get worse with budget (2608.12150).
- Cascades inside one model: **DART (2606.23181, EMNLP 2026 Findings)** — two no-think drafts; agree → answer; else think with an
  entropy-predicted budget; +9.0 math, +22.5 code, 32–73% fewer thinking tokens; fixed caps flat (Qwen3-8B MATH-500 69.25 / 69.75 /
  70.00 / 72.25 at 1k / 2k / 4k / 32k). **The Coupling Tax (2605.07686)** — no-think first, escalate on an unfinished answer; the
  fallback must be long enough (Qwen3-8B GSM8K: −15 net at 512, +42 at 1,024, +77 at 2,048). HRBench (2605.28398; speculative no-think →
  think on keywords / entropy, largest on code), CopT (2605.20075), learned routers (AdaptThink 2505.13417, Thinkless 2505.13379,
  AutoThink 2505.10832, Learning When to Think 2608.20256). Demystifying Hybrid Thinking (2510.12680) uses "leak" for reasoning in the
  no-think mode — not our passing-but-wrong program.
- Allocation: compute-optimal test-time scaling (Snell et al., 2408.03314; needs difficulty estimates), learned allocation (2410.04707),
  consistency-gated cascades between models (Yue et al., 2310.03094, ICLR 2024), OptiMind (2509.22979: gpt-oss-20b OptMATH 74.9 → 90.3
  with 8-sample majority, 86.5 with 5 rounds of execution feedback).
- Placement: HO-SB consistent with DART / Yue (a cascade is as good as its gate) and against "no-think is enough" (2504.09858, Coupling
  Tax) where the check leaks — new for OR programs; HO-SB4 consistent with the Coupling Tax; HO-PB consistent with DART's shuffled-budget
  control, the few-label negative is new; HO-4K consistent with DART's flat caps (reported with the first program apart: +2.4 first
  program, +0.6 end); HO-SEED new; HO-CM's kind of gain known (2506.04210, OptiMind), conditional on a visible failure new.

**Tool calling (TC-1).** Verified: Qwen3 report BFCL v3 thinking 68.1 / non-thinking 60.2 (8B); 2608.22472 ("Small Reasoning Models are
Instruction Followers in Function Calling") — 74.5 → 83.3 live is inside its IFFC prompting, native FC with thinking 75.5 live / 88.8
non-live; Reasoning Trap (2510.22977) distractor-tool hallucination 36.2 → 56.8% (Qwen3-8B); ThinkBrake v1 oracle stopping 85.8 → 94.2
(v5: ~90.7 → 95.4); CopT 85.77% @ 235 → 86.45% @ 168 tokens (contrastive reverse-KL score); Reinforced Agent (2604.27233, a separate
reviewer model); ComplexFuncBench 78.8% value errors (Qwen2.5-72B). No paper gates a hybrid model's thinking on tool calls with a
deterministic schema check.

**Instruction following (IF-1).** Verified: Li et al. 2505.11423 (NeurIPS 2025), 2606.09662 (10–20% of IFEval prompts flip with Qwen3
thinking; planning constraints helped, precision constraints hurt), DVR 2410.12207 (Findings ACL 2025), NSVIF 2601.17789 (VIFBench), AutoIF
2406.13542 (ICLR 2025, training data), HRBench (no IF). **Closest: ProgCo (2501.01264, ACL 2025)** — self-written verification program,
executed, then refine, with reflection on the program (IFEval GPT-4o 83.0 → 88.0, 91.3 with real Python; correct → incorrect flips 15.4%
vs 35.2% without its contrast step). Also TICK / STICK (2410.03608), Instruction Boosting (2510.14842, judge 73% accurate), training-time
verifiers (Tülu 3 RLVR 2411.15124; IFBench 2507.02833; VerIF 2506.09942; RECAST 2505.19030; IFDecorator 2508.04632), self-correction that
does not change the output (Blind Spot 2507.02778; Feedback Friction 2506.11930; Huang et al. 2310.01798), model-written tests failing
right outputs (2501.12793), CounterRoute (2609.29109, an RL router between Qwen3 modes). New in IF-1: the executed self-written checker as
the gate for the thinking mode, rewrite vs think under the same gate, IFBench at inference time, measured false-alarm and copy rates.
Likely reviewer asks: a ProgCo-style reflection on the checker; AutoIF-style cross-checks of the checker.

**Sampling (2026-10-27 14:4x UTC, for SAMP).** Qwen3.5-9B card: thinking general T 1.0 / top-p 0.95 / top-k 20 / presence 1.5, precise
coding T 0.6 / 0.95 / 20 / presence 0; Qwen3 report evaluates thinking at T 0.6 (presence 1.5 only for creative writing); Nemotron-3-Nano:
T 1.0 / top-p 1.0 reasoning, T 0.6 / 0.95 tool calling. Sampling sensitivity of reasoning models: A Sober Look (2504.07086, up to 15
points from temperature), temperature diversity (2510.02611), repetition penalty and code (2505.10402). Budget-forcing studies mostly
match decoding across arms (Coupling Tax, HRBench greedy; ThinkBrake official presets); DART drafts at T 0.6 and thinks greedily. Our
mismatch (cut think at T 0.7, full think at the general preset) is tested in PREREG_SAMP.md.

**Contest code (2026-10-27 16 UTC, for LC-1; IDs and numbers opened).** DART (2606.23181): its code gate runs the non-thinking drafts on
the reference tests that later score them (accept precision 100% by construction, its Limitations); on half of each problem's assertions
precision is 92.5 / 97.9 / 98.1% (Qwen3-8B / 14B / 32B); HumanEval and MBPP only. PaT (2605.07248): examples + model-written tests gate an
escalation to planning, non-thinking Qwen3. Test-gated model cascades for code (2405.15842, −26% cost). S* (2502.14382): public tests
drive revision and selection on LiveCodeBench, tokens not counted. Self-Debugging (2304.05128), CodeT (2207.10397), AlphaCode sample
filtering (2203.07814), Olausson et al. (2306.09896). Trained mode routers: Thinkless, AdaptThink, AutoThink (math), LHRM (2505.14631, also
LiveCodeBench). Qwen3 report LiveCodeBench v5 (32k): 8B 57.5 / 22.8, 14B 63.5 / 29.0 (thinking / non-thinking). No published rate of
programs that pass LiveCodeBench's samples and fail its hidden tests. In the project: HO-CC / HO-CAP (Codeforces geometry) are the
reference; LC-1 asks whether their contest boundary is contest code or that set.

## Related-work check 2026-10-29 (2026-10-29 11:0x UTC): the check as the bottleneck, tuned checks, next directions

- **Closest to the thesis (abstract pages opened):** *Cheap Verifiers, Large Blind Spots* (arXiv 2609.01345, Sep 2026): a cheap student
  answers, a frontier model verifies; the verifier's blind spot β (wrong answers it accepts) rises from 0.12 to 0.55 as the student grows
  from 0.5B to 32B, a frontier verifier (β ≈ 0.05) escalates 46% of hard MATH against a 39% true error rate, the cascade's own metrics show
  3% error while the true error reaches 32%, bound ε∞ ≲ q₀β₀; corrective fine-tuning on the verifier's rejections degrades the student.
  *Partially Correlated Verifier Cascades* (2607.13918, Jul 2026, theory + synthetic only): correlated gates give concave log-odds,
  polynomial reliability and a blind-spot ceiling; two repeated verdicts identify the correlation; "the practical lever is decorrelation"
  (another family, modality or evidence source). → Our "the check decides" is their β measured inside one hybrid model with free
  execution checks, against fact-matched thinking, on six task types; our leak does not shrink with size (HO-32), consistent with their β
  rising. What stays ours: the within-model think / no-think cascade, the fact-matched baseline, the per-task split. Their correlation
  model is untested on real tasks; our seeds, modes and models give repeated verdicts to test it offline.
- **Trained checks for text-to-SQL (search snippets, not opened):** outcome reward models for test-time verification (2606.30851),
  SQL-Checker (WWW '26), a label-free verifier on generated small databases (PVLDB vol. 19), SpotIt (2510.26840, gold queries often
  wrong), CHASE-SQL's fine-tuned pairwise selector (2410.01943), Generative Verifiers (2408.15240). All use labels and select among
  candidates; none gates a hybrid model's thinking. No paper found that distils a model's own thinking-mode review into a cheap gate.
- **Agents:** HybridAgents (2610.18861; latent vs text reasoning with tool calls, a learned switch), HRBench (2605.28398): no
  check-gated thinking per step found.
