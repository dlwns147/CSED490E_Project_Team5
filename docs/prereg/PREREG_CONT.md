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

## Addendum A: agreement as the stop signal (written 2026-10-31 01:5x UTC; predictions above unchanged)

Written while the main rows accumulate (103–119 of 202 OptiBench, 14–31 of 82–100 on the other sets per seed so far); only row counts
were seen, no outcome of any main row. The 4-problem BWOR smoke (tag q8bsmoke, not part of the results) was read earlier. Analysis
`poc/analyze_conta.py` (written and tested on synthetic rows before any main row was analyzed); run after `analyze_cont.py`, on the
same rows.

**Why.** CONT's early exit stops at the first forced program that passes, and on word problems a passing program is often wrong
(stored: right | passes 76 / 62 / 61 / 34%). The project's best label-free signal is agreement between two answers (HO-PA, CC-P2), and
the peer cascade has already paid for two cheap programs (Qwen3-8B's, N, and Qwen3.5-9B's, the peer) when it escalates to the default.
**Exploration on stored rows** (other runs; it chose the design, it is not evidence for the predictions): a passing 2,000-token cut
program that agrees with the peer's quick program is right 85 / 88 / 95 / 36% (OptiBench third / BWOR / LogiOR / OptMATH), with N's
84 / 79 / 92 / 32%, with neither 36 / 39 / 34 / 27%; requiring agreement before accepting the cut program inside the peer cascade
gains +2.1 accuracy points at +3.1k tokens (+0.59 [−0.64, +1.78] utility over SB→T→T; LogiOR +2.88, OptMATH −1.43); requiring it of
the full think as well loses (−0.11): the stricter check pays only if the tokens it adds come back, which exits inside the fresh think can do.

**Theory.** For a problem with right value y* and two answer sources with value distributions a and b (sampled independently given the
problem), P(right | they agree) = a(y*)b(y*) / Σ_y a(y)b(y): agreement is precise when the wrong values are spread and imprecise
where the two share a wrong mode (one wrong formulation). Two forced programs of the same think share its prefix, the formulation in
progress, so their wrong values coincide most; N's quick program shares the model; the peer shares neither. Predicted order of
precision: the peer ≥ N > the same think's earlier program. The exit value at cut c is CONT's with "passes" replaced by "agrees":
fewer exits, a smaller leak.

**Prior work (IDs opened 2026-10-31).** Stop sampling once samples agree: Adaptive-Consistency (2305.11860, EMNLP 2023), ESC
(2401.10480, ICLR 2024); probe the answer at fixed intervals of a think and stop when consecutive probes agree: Dynasor-CoT (Certaindex,
2412.20993), Answer Convergence (2506.02536). **New here:** the anchor is an answer the cascade already paid for (another model's cheap
program) rather than the same think's earlier answer, on executed programs with the free check, with cut points fitted under a token
price; and a test of which anchor is precise, against the theory.

**Policies** (per problem and seed, the thinks of this run; N and the peer = the stored formx rows of the same seed, the peer run only
when N passes, as HO-PA): **RD** as above; **RDc** = RD whose exits inside the fresh think need the forced program to pass and agree
with an earlier passing forced program of that think (convergence); **PR0** = N passes and the peer agrees → N, else R0 (reported);
**PRA** = N passes and the peer agrees → N; else every later program (the cut of think s, the forced programs of think s2 at S) answers
only if it passes and agrees with an earlier passing answer of the stream (N, the peer, the cut, earlier forced programs); think s2's
end answers if it passes, then think s3's end; if none passes, the last passing think program. S for RD / RDc / PRA: greedy forward
selection, cross-fitted, as above.

**Predictions** (same intervals and utility as above):
- **CA-P1:** RDc − RD: utility lower bound > 0.
- **CA-P2 (the claim):** PRA − the stored default SB→T→T: utility lower bound > 0.
- **CA-P3:** PRA − the stored peer cascade N→q35→SB→T→T: utility lower bound > 0.
- **CA-P4 (the mechanism):** among passing forced programs (every cut of every think), right | agrees with the peer's quick program −
  right | agrees with the latest earlier passing forced program of the same think: lower bound > 0 (bootstrap over problems).
- Reported: the precision table by anchor (peer, N, the same think's earlier program, none), the fitted points, per benchmark, PR0.

**Decision.** P2 and P3 hold → on word problems the default becomes the peer cascade with agreement exits (the free check inside the
think is agreement with answers already paid for; PROJECT / REPORT / PROPOSAL), and the same is pre-registered on SQL. P2 holds, P3
refuted → reported as a gain over the default only. P4 holds → exits anchor on another model's answer, not on the think's own earlier
answer (reported against Dynasor-CoT / Answer Convergence); P4 refuted → the theory's independence ordering fails here. P1 holds →
convergence exits beat pass-only exits inside a think.

Expected (not a rule): P1 refuted, P2 inconclusive (+0.5 to +2), P3 inconclusive, P4 holds (+5 to +15 points).

**Run note (2026-10-31 03:0x UTC; no outcome seen, predictions unchanged).** OptMATH runs at about 20 problems per hour per seed (its thinks reach
the cap most often), 3 hours behind the other sets. Three helper jobs (1286131–1286133, `run_cont.py` with `CONT_REVERSE=1`) take
its problems in reverse order into `cont_q8b_optmath_s<seed>_rev.jsonl` with the same per-problem seeds; when the two files of a seed
cover all 100 problems both jobs are cancelled. `analyze_cont.py` reads both files, the main job's row winning where both ran a problem.

## Results (2026-10-31 05:3x UTC; `results/cont.txt`, `results/conta.txt`)

All 476 problems × 3 seeds (OptMATH: main and reverse-helper rows merged, every problem covered). An interim run of both analyses
(05:2x, OptMATH 97 / 100) was read before the last three problems landed; nothing was changed after it.

| test | utility (95% interval) | verdict |
|---|---|---|
| CT-P1 RD − R0 (early exit at the first passing forced program) | +0.39 [−0.48, +1.29] | refuted (not shown) |
| CT-P2 C0 − R0 (continue the cut think instead of restarting) | +0.26 [−0.23, +0.77] | refuted (not shown) |
| CT-P3 D = P(fresh end right) − P(same end right) after a failed 2k check | +1.29 [−2.15, +4.72] points | refuted (not shown) |
| CT-P4 CD − RD | +0.07 [−0.87, +1.08] | refuted |
| CT-P5 CD − the stored SB→T→T | +1.22 [−0.98, +3.44] | refuted (not shown) |
| CA-P1 RDc − RD (convergence exits) | −0.39 [−1.29, +0.48] | refuted |
| CA-P2 PRA − the stored SB→T→T | +1.22 [−0.90, +3.46] | refuted (not shown) |
| CA-P3 PRA − the stored peer cascade | +1.21 [−0.84, +3.36] | refuted (not shown) |
| CA-P4 right \| agrees with the peer − right \| agrees with the think's previous passing program | +10.6 [+6.9, +14.3] points | **holds** |

Policies (accuracy @ tokens, utility): R0 53.9% @ 9.90k, 48.90; C0 53.8% @ 9.24k, 49.16; RD 53.9% @ 9.27k, 49.29; CD 53.8% @ 8.86k,
49.35; PRA 55.8% @ 12.92k, 49.35; **oracle** (the first right program of the think) 60.3% @ 11.20k, **54.69**; stored SB→T→T 53.2%,
48.13 (R0 replays it within 0.8). Fitted cut points differ between the halves ((5k, 8k, 14k, 15k) vs (3k, 4k, 7k, 10k, 15k)): no
stable stopping point. Per benchmark the exits gain on BWOR / OptMATH (+1.2 / +1.7 over R0) and lose on LogiOR (−2.2), all n.s.

**Hazard (the mechanism).** A forced program passes the free check 60–63% of the time from 1k to 4k thinking tokens and is right when
it passes 64–65% of the time; later cuts are less precise, not more (53% at 7–9k, 37–40% at 13–15k: the thinks still running there are
the hard problems'), and the end program is right 69.7% of the time it passes. So the early program is about as good as the end
program the think was going to write, and the exit saves only where the think is long, which is where its programs are least precise.
Precision by anchor (CA-P4, every passing forced program): agrees with the peer's quick program 76.7% right (47% of them), with N's
71.9% (40%), with the same think's previous passing program 66.2% (68%), with nothing 25.2% (17%) — the order the independence theory
predicted (peer ≥ N > the same think), and convergence of a think's own probes (Dynasor-CoT / Answer Convergence) is the least precise
anchor on word problems: the think converges on its formulation, right or wrong. Zero values are not the leak (147 of 2,572 wrong
passing forced programs print 0).

**Continue vs restart (CT-P2 / P3).** Under independence (D = 0) the theory predicted C0 − R0 = +0.37; the measured +0.26 [−0.23,
+0.77] and D = +1.29 [−2.15, +4.72] points fit both D = 0 and the break-even D = 1: 233 escalated problems are too few to tell
whether a failed cut predicts its own think's failure. Neither the restart nor the continuation is shown better.

**The gap.** The early-exit oracle sits +5.8 utility above R0, larger than the perfect check on the cheap path (+2.3, PREREG_TD.md
note, HO-PA ceiling with a perfect peer), and every label-free stop signal recovers at most a fifth of it (+0.4 to +1.2, n.s.): passing
forced programs are right 60–65% of the time, and agreement lifts that to 72–77% for half of them. The bottleneck is the check's
precision, not where it is applied.

**Decision (as pre-registered).** P1 refuted → the default does not stop at forced programs; P2 and P3 refuted → neither restart nor
continuation is shown better at this size, the default keeps restarting (its stored form); CA-P2 / P3 not shown → the peer cascade
with agreement exits is not adopted; CA-P4 holds → where a cascade anchors an exit on agreement, the anchor is another model's answer,
not the think's own earlier answer (reported against Dynasor-CoT / Answer Convergence). No CONT run on SQL or contest code (that
was conditional on P1 and P5). Next: the check itself — a verifier trained with labels on OptMATH-Train (PREREG_VER.md).
