# Pre-registration CONT: the free check inside the think — where to stop it, and whether to continue it after a failed check

Written 2026-10-30 23:5x UTC, before any main row (`poc/run_cont.py`; a 4-problem smoke on BWOR runs alongside to test the harness and is
not part of the results). Results go below.

**Why it could change the claim.** Every gain so far is on the cheap path. On word problems the cheap path saves nothing, and the cost
sits in the default: Qwen3-8B's SB→T→T spends 5.2k (OptiBench third), 13.1k (BWOR), 14.2k (LogiOR) and 13.5k (OptMATH) tokens per problem —
6.5–7 utility points on the three hard sets, more than any cheap-path gain measured (stored rows; the peer cascade's N and peer programs
together cost only 0.8k + 0.6k there). The default uses the free check only at its seams: after the 2,000-token cut think (fails 49–55% on
the hard sets) it **restarts** a full think from nothing (11.0k tokens on average, its program fails the check 39–40% of the time), and
after that a third. Two questions about that design are open and are the same question for every task with a free check:
(a) **early exit**: the program can be forced at any point of a think and checked for free, so the think can stop at the first point
where the program passes, instead of only at its end; (b) **continue or restart**: after the cut program fails, the same think can
continue (2,000 tokens already paid) instead of starting a new one. If either pays, the default changes on every task; if (b) does not,
the reason is measurable (below).

**Theory (λ = 0.5 utility points per 1,000 tokens; 2,000 tokens = 1 point).**
- *Continue vs restart.* Both answer with the cut program when it passes; on a failed check, restart pays a fresh think of length L′,
  continuation pays the rest of the same think, L − 2,000. If, given the problem, a think's end is independent of whether its 2,000-token
  cut passed (H0), continuation saves exactly 2,000 tokens per escalated problem-seed at equal accuracy: C0 − R0 = P(cut fails) × 1.0
  = **+0.37** pooled (36.7% of Qwen3-8B's cut programs fail the check in the stored rows; 16 / 49 / 55 / 51% per set). Otherwise
  C0 − R0 ≈ P(cut fails) × (1.0 − 100·D), where D = P(a fresh think's end is right | the cut failed) − P(the same think's end is right |
  the cut failed). **Continuation pays only if D < 1 point**: the restart's independence is worth more than 2,000 tokens as soon as a
  failed cut predicts the same think's failure by more than one point in a hundred. Expected: D > 1 point (a think that wrote a failing
  program at 2,000 tokens has committed to its formulation), so restart wins — the theory would then explain the default's design.
- *Early exit.* Checking the forced program at cut c (given the think still runs and nothing stopped it before) is worth
  100·[P(passes, right, the policy's later answer wrong) − P(passes, wrong, later answer right)] + λ/1000·[P(passes)·(tokens the rest
  would cost) − program tokens at c]. The leak term is why it can lose: Qwen3-8B's passing cut programs are wrong 24–66% of the time
  (stored: right | passes 76 / 62 / 61 / 34%). A check costs a whole program (0.4–1.4k tokens on these sets), not a short trial answer
  as in DEER, so checking often is expensive; which points pay is computed from data (below), not chosen.

**Prior work (2026-10-30 23 UTC; IDs opened).** Early exit by trial answers' confidence at thought switches (DEER, 2504.15895); stop when
the answer stops changing (Answer Convergence, 2506.02536, EMNLP 2025; ES-CoT, 2509.14004); hidden-state probes of the intermediate
answer (2504.05419; LYNX, 2512.05325, with conformal calibration); a self-assessed sufficiency check at reflection points that resumes the
same trace when it fails (DTSR, 2604.06787); a cost-aware comparison of exits that charges the probes (2606.30852: learned stoppers win on
Qwen3 math, none certifiable on AIME / GPQA; probe overhead decides whether a policy saves). Restart strategies for randomized
algorithms with a verifier (Luby, Sinclair & Zuckerman, IPL 1993): with a reliable check, a fixed-cutoff restart is optimal. Budget
forcing (s1, 2501.19393) is how the cut is made. Closest: an unreviewed study (ExecExit, github.com/Mrch1io/execexit; Qwen3-8B and two
R1 distills, 199 LiveCodeBench problems) delivers the first draft within 4,096 thinking tokens that passes the public examples:
7.9% fewer tokens, −1.9 [−3.4, −0.6] points, not shown safe — the leak, on code. In the project: the 2,000-token first think and the
restart-then-retry order (HO-CM, HO-PB, HO-4K, HO-SEED). **New here:** the free check as the stop signal inside a restart cascade, its
points derived from data and cross-fitted under an explicit token price (not a fixed window); continue vs restart after a failed check,
tested against a theory that names the condition (D < λ·2,000 tokens); a value check on word problems, where the leak is large.

**Run.** Qwen3-8B (`poc/run_cont.py`, tag q8b, one RTX 3090 per job, vLLM `--max-model-len 24576`), the four held-out word-problem sets
(OptiBench third via `FORM_SUBSET=0/3`, BWOR, LogiOR, OptMATH; 476 problems), seeds 1–3, formx's prompt (the same similar-problem
program), the harness sampling of the stored cut and full thinks (T 0.7, top-p 0.95), per-problem seeds as run_form. Per problem and
seed: one think of at most 16,000 tokens; from that same think, the program forced every 1,000 thinking tokens (budget_chat's cut text)
and the program at its end (as the stored full think: 16,000 tokens in all, no program if the think reaches the cap). Cut programs are
branches; the think never sees them. Analysis `poc/analyze_cont.py` (written before any main row):
- R0 = restart (SB→T→T from these thinks): the 2,000-token cut of think s; on a failed check the end of think s2; on its failure the end of think s3.
- C0 = continue: the cut of think s; on a failed check think s to its end; on its failure the end of think s2.
- RD(S) / CD(S) = R0 / C0 with the think after the cut checked at the points S (first passing program answers).
- S is chosen by greedy forward selection over 1,000 … 15,000 on one half of the problems (crc32(id) % 2), scored on the other half,
  and the reverse (cross-fitted); tokens = thinking tokens to the stopping point + every program generated.

## Predictions (476 problems × 3 seeds; paired 95% intervals over problems, seed means; utility = accuracy − 0.5 × ktokens)

- **CT-P1 (early exit):** RD − R0: utility lower bound > 0.
- **CT-P2 (continue):** C0 − R0: utility lower bound > 0.
- **CT-P3 (the mechanism of P2):** D (above) lower bound > 0.
- **CT-P4:** CD − RD: utility lower bound > 0.
- **CT-P5 (the claim):** the better of RD / CD (higher cross-fitted mean) − the stored SB→T→T default (other runs of the same model):
  utility lower bound > 0.
- Reported, not decided: per benchmark; the fitted points; the hazard table (per cut: the think still running, the program passing,
  right when passing, its tokens); the early-exit oracle (first right program of a think); R0 − stored SB→T→T (replay sanity: same
  sampling, other runs); the raw thinks around accepted wrong cut programs.

## Decision

- P1 and P5 hold → the default checks the forced program at the fitted points of the full think and stops at the first that passes
  (PROJECT / REPORT / PROPOSAL; the recipe's "free check at every step" extends inside the think); the same is pre-registered on SQL and
  contest code next. P1 holds, P5 refuted → reported as a gain over the replayed default only.
- P2 holds → the second step continues the cut think instead of restarting. P2 refuted, P3 holds → the restart is justified by measured
  dependence (D above the break-even), reported as the reason for the default's order. P2 and P3 refuted → neither shown at this size.
- P4 holds → continuation and early exit combine; refuted → early exit is applied to a fresh think only.

Expected (not a rule): P1 holds (+0.5 to +2), P2 refuted, P3 holds (D 3–10 points), P4 refuted, P5 inconclusive.
