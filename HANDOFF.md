# Handoff: continuing the project on new servers

State as of 2026-10-13 08:00 UTC. All GPU work on the old servers has been stopped and the hourly loop cancelled.

## 0. Server 2 status (2026-10-13 14:00 UTC)
STATUS 05:38 (10-17, hourly-cron session sj-46): X6 queued (poc/queue_s2_x6.sh, waiter pid 2120997): when the X1 q32b re-run ends and
GPU1 is empty it regrades + analyzes X1 q32b (results/x1/analysis_q32b.log) and runs Qwen3-32B thinkf (thinking + API snippet) on X3,
seeds 1-3, port 8062 -> analyze vs mip/mipf/think and FACT-FIRST-THEN-THINK (PREREG_X3.md X6). GPU3 = U2 (experiment session).
STATUS 05:36 (10-17, experiment session): U1r q8b DONE (fact-first-then-think best on all 3 cure seeds; PREREG_U1.md). analyze_u1.py now
also prints FACT-FIRST-THEN-THINK. RUNNING: U1r q32b (GPU0) / q36 (GPU2) think arms; U2 retrieved-fact geometry arm on GPU3
(queue_s2_u2.sh, tags geocross_S2_U1_<m>_geo_retr_s1-3; CO retrieved arm = existing decor_s*); X1 q32b think GPU1 (~1491/1680).
STATUS 04:36 (10-17, hourly-cron session sj-46): VIEWS-P5 Qwen3.6 replication recorded (PREREG_VIEWS.md: kappa 0.74 holds; thinking
+5.0 refutes <=+2, but its net gain is all in popular bins: compute recalls weakly-held facts, never adds missing ones). GPUs 0-3 busy
(U1r by the experiment session; X1 q32b think GPU1). Two sessions are on this project: check queue_log / PREREG tails before launching.
Suggested next after U1r: RETRIEVED-fact-first-then-think (BM25 snippets / retrieved hint instead of the hand-written FACT) vs MECHANISM,
and PopQA with a retrieval view (does a retrieved passage decorrelate knowledge errors?).
STATUS 04:34 (10-17): U1 DONE (PREREG_U1.md: mechanism 82.5 > difficulty 73.9; fact-first-then-think 87.2 best; Snell-binned 78.7).
RUNNING: U1r seeds 2-3 of cure arms (queue_s2_u1r.sh, GPU0 q32b / GPU2 q36 / GPU3 q8b, resumable, retries) -> for s in 2 3:
U1_CURE_SEED=$s python poc/analyze_u1.py (also compute fact-first-then-think); X1 q32b thinking on GPU1 (then regrade + analyze_x1.py q32b).
STATUS 03:31 (10-17): U1 Qwen3-8B DONE (results/u1_q8b.log; mechanism 66.8 vs difficulty 62.0 pooled); U1 q32b / q36 think still running
(GPU0 / GPU2, resumable). X1 Qwen3-32B thinking resuming (GPU1, 410/1680 rows). VIEWS-P5 PopQA Qwen3-8B DONE (kappa 0.75-0.91, leak
38-63%); replication on Qwen3.6 running (GPU3, queue_s2_x5b.sh -> results/x5/analysis_q36.log).
STATUS 02:56 (10-17): second server die-off (host load ~2,800, swap full; 5 orphaned lean procs of mine killed). Resumable re-run
with retries: poc/queue_s2_rerun_think2.sh (U1 think GPU0 q32b / GPU2 q36 / GPU3 q8b; X1 q32b think GPU1). Each lane logs a final
'S2_U1 think <tag>: geo n/108, co n/100' line. Then analyze_u1.py; regrade + analyze_x1.py q32b.
STATUS 02:26 (10-17): re-runs progressing (~2-3k tok/s per server): U1 think requests done q32b 96/208, q8b 150/208, q36 10/208 (Qwen3.6
thinks up to 28k: hours); X1 Qwen3-32B thinking 187/1680 rows (resumable; ~10 h). VIEWS-P4 running in background
(poc/analyze_views_p4.py -> results/views_p4.log).
STATUS 00:29 (10-17): all servers died 23:51:25 (NCCL watchdog, all engines at once). Re-running the lost THINK arms
(queue_s2_rerun_think.sh): U1 think on GPU0 q32b / GPU2 q36 / GPU3 q8b (then python poc/analyze_u1.py), X1 Qwen3-32B thinking on GPU1
(resumable; then regrade + analyze_x1.py q32b). Harnesses now flush rows as they complete.
STATUS 23:47: VIEWS meta-analysis DONE (PREREG_VIEWS.md: P1/P2 refuted across domains, P3 holds loosely; within a fixed first view,
the less correlated second view leaks less 13/14). U1 thinking arms running (CO think ~17% after ~1h; geo think pending) -> then
python poc/analyze_u1.py. X1 Qwen3-32B thinking: 6 requests left -> regrade q32b_think files, then analyze_x1.py q32b.
STATUS 22:30: U1 RUNNING on GPUs 0 (q32b, port 8043), 2 (q36, 8045), 3 (q8b, 8056; queue_s2_u1_q8b.sh) -> analysis poc/analyze_u1.py
(still to write, before reading results). X1: gpt-oss + Qwen3.6 done; Qwen3-32B thinking: 22 requests left on GPU1 (8044) -> regrade + analyze.
X3 done (both models). X4: Qwen3.6 Lean check running (CPU) -> results/x4/lp_q36.log. VIEWS meta-analysis still to do.
STATUS 21:44: X4 done for gpt-oss-20b (66/244; feedback / fact-feedback / fresh all ~3%) and Qwen3-32B (31/244; log-prob AUROC 0.60);
X4d Qwen3.6 Lean gen + check + lp running on GPU2 (queue_s2_x4d.sh). X1 Qwen thinking + X3 Qwen3-32B thinking: long tail still running
(KV cache full, ~300 tok/s). NEXT: VIEWS meta-analysis (PREREG_VIEWS.md; offline, per-item correctness of view pairs from X1, X3, N12,
N15, N17, N19) and the X1 / X3 thinking analyses when they finish; U1 starts after X1 + X3.
STATUS 20:29: X4 gpt-oss-20b DONE (66/244 proved, 32.6% of proof-giving attempts cite non-existent names); X4b running on GPU2
(queue_s2_x4b.sh: feedback-vs-fresh round -> results/x4/fix_oss20_test.jsonl, then Qwen3-32B gen with log-probs + check). X1 Qwen thinking
and X3 Qwen3-32B thinking still running (GPUs 1/3, 0) at 20:29 — slow (28k / 16k caps).
STATUS 19:30: X2 DONE (verified reuse ~100% but only 47-60% templates; hybrid +2 pts at 59-89% tokens). X3 gpt-oss-20b DONE, Qwen3-32B
running (GPU0). X1 Qwen thinking running (GPU1, GPU3). X4 gpt-oss-20b miniF2F gen running (GPU2, queue_s2_x4.sh; Lean checks on CPU via
poc/run_lean.py check). U1 waits for X1 + X3. Next: X4 Qwen runs with --logprobs + the 'unknown name' feedback round (fix mode to write).
USER 18:3x (2): 'go beyond computation, diverse math' -> math ladder: X1 competition math (running), X2 numeric variants (running),
X3 word problems -> optimization models (PREREG_X3.md; queue_s2_x3.sh waits for X2; GPUs 0+2), X4 Lean 4 miniF2F (setup running in
/SSD/lean_postech, setup_lean.log; predictions in PREREG_X3.md), then U1 (waits for X1 + X3).
USER 18:3x: computation-only topics feel superficial / debug-like -> research question PREREG_VIEWS.md (error correlation between a
model's views predicts self-verification; offline meta-analysis over stored settings next, PopQA views after U1).
USER 18:2x: proposal reads as heuristic / debugging -> draft reframing results/PROPOSAL_CORE_DRAFT.md (three mechanisms + signatures;
allocation by mechanism vs difficulty), decisive test U1 (PREREG_U1.md). Queue 18:29: X1 thinking lanes running (GPU1 Qwen3-32B, GPU3 Qwen3.6; regrade every file with
`python poc/run_math.py --regrade <files>` before analysis: X1 processes started before the grading fix write all-0 grades), X2 running on
GPU0 (q32b) + GPU2 (oss20 then q36), U1 waiter waits for 'S2_X1 runs done' AND 'S2_X2 runs done'.
X-track (other kinds of math) STOPPED in the writing session 17:57; the user then asked the EXPERIMENT session (18:0x) to suggest and
test other math: X1 (PREREG_X1.md, unchanged + addendum P6) RUNNING since 18:01 on GPUs 0-3 (poc/queue_s2_x1.sh; outputs
results/x1/math_<model>_<text|prog|think>_s1-3.jsonl). poc/run_math.py was rewritten by the experiment session (it overwrote the prepared
version by mistake at 18:00; same data + math-verify grader). Analysis to write: gate text==prog -> think; leak = wrong share among agreeing pairs.
LOOP: hourly cron b5f2cb76 ('7 * * * *', session-only) created 2026-10-13 16:20 UTC, auto-expires ~2026-10-20 16:20: recreate on
10-19 if the project continues. User 2026-10-14: keep suggesting and testing METHODS with related-work checks (memory file).
PROPOSAL 2026-10-16 17:4x (user, writing session): PROPOSAL.md / PROPOSAL_ko.md = compact, plain-language proposal with figures:
0 background, 1 why it matters + fig0 (fix flow), 2 question/test, 3 R1 facts (fig10), R2 reuse + adapt (fig12, fig16),
R3 checks leak + pay on failure + second opinion (fig13, fig14, fig15), R4 fix by problem type + library (fig17), 4 mechanisms,
5 baselines + our methods, 6 related/plan/limits. Figures: poc/make_figures_explain.py. Update numbers in place; keep it compact.
Keep them compact: update numbers in place, put details in FINDINGS / PREREG; old long version results/archive/*_before_compact_2026-10-15.md.
CURRENT STATE 2026-10-15 09:40 UTC (read this first): all GPU servers stopped. Methods summary = PREREG files (was PROPOSAL 4.4 table);
pre-registrations + results in results/PREREG_*.md (V = reuse, N = contest methods, FM = fact mining, D1 = distillation,
H1-H6 = hard benchmarks). Working methods: V1 verify-once-reuse (routing, job-shop, synthetic; cost curve fig12), N2 repair,
N3 cascade; V1x: reused programs transfer to Homberger 200 (60/60). Closed negatives: N1, N5, N6, FM, V2/V3, V1p (portfolio:
shared failure), D1-D3. H2d/H2e done and replicated: gpt-oss-120b high = 66.2% over 3 seeds at 30.1k tokens (64k cap).
F2R done (F2 replicates on Solomon; PREREG_F2R.md). Failure->fix map draft: results/FIX_MAP.md (plan item 3). All planned
experiments done (V1x-J too). Open: closed API model (no access). Done 08:4x 10-16: N9 seed 1 (PREREG_N), H7 contest + Solomon
per-instance (PREREG_H7; V1 reuse on q36 via analyze_reuse_curve.py -> results/h3/reuse_curve_q36.log, CPU). Running 08:34 10-16:
N10 + N11 DONE 09:15 (negative: error-signal routing and probe-then-commit lose to per-domain defaults; PREREG_N10.md);
N10 stage 2 LLM router DONE (P4 holds, worse). N10-M3 done except thinking (16k cap truncated; re-run 48k: queue_s2_n10m3t.sh GPUs 1+3). N12 (agreement gate, PREREG_N10.md)
seed 1 done; geometry seeds 2-3 done (replicated: = thinking accuracy at 61-79% tokens); optimization seeds 2-3 thinking arms
running (queue_s2_n12r.sh GPUs 0+2) -> poc/analyze_n12.py 2 co / 3 co; M3 N12 after the thinking re-run. N13/N13b done (PREREG_N:
oracle gate = always-high accuracy at 82% tokens). results/CRITIQUE.md = standing constructive critique (user 10-16); next: reuse under
changed rules = N14 (PREREG_N14.md; 2606.04816 read: it is a verifier, not editing): sources poc/n14_sources.py -> results/n14/,
N14c DONE 11:29 (job-shop + release dates: adapt verified >> scratch, Qwen3-32B 30/80 vs 4/80, gpt-oss-120b 80/80 vs 72/80).
N14d/N14c2/N14e DONE 12:30 (PREREG_N14.md; tard/flex references re-running with free CPU -> results/h5/{tard,flex}/ref.json,
then recompute 'within 5%' with the analysis in results/h5/n14ce_analysis.log's script). DONE 14:45: seed-3 replications (N15d portfolio, N14c adapt: hold), N16 (log-probs flag invented API names, AUROC 0.84-0.90, but
always-snippet beats any trigger; PREREG_N16.md; run_co --logprobs + llm.chat_msgs(logprobs) added). USER 14:3x: analyses must report
tokens / finish / failure kinds / log-probs, not only accuracy. P1 (prompt rewording: robust), N17 (cross-model second opinion: 41% / 8.8%), results/CHECKS.md (check coverage) DONE 16:32.
N18, N12-M4 (Qwen3-8B: agreement gate > thinking), N19 (contest tool-condition gate fails for gpt-oss: shared mistakes) DONE 17:08.
All GPUs idle at 17:08. Next candidates: decorrelation as the explicit criterion for second opinions (measure error correlation of
candidate checkers before using them); a closed API model if access appears. Older: N18 was (queue_s2_n18.sh, GPUs 0-2, tag cc_full_q36_lp_s1-3 with lp / lp_tok;
pre-registered in PREREG_N.md: AUROC of mean / min / q5 log-prob for correct vs wrong example-passers, selection by confidence,
where the low-confidence tokens fall). run_cc.py has --logprobs and --para now.
Older: N15e / N15f DONE 14:20. RUNNING 14:21 (done): seed-3 replication of N15 + N14c
(queue_s2_rep3.sh, GPUs 0-3; then re-run analyze_n15.py / analyze_n15d.py with seed 3 added (scripts read seeds 1-2: extend) and the
N14c table). flex + tard references re-run done. Older: N15 / N15b / N15c / N15d DONE 12:48. N15e was:
(queue_s2_n15e.sh, GPUs 0-3, tags results/h5/sol_<m>_{none,cpsat,mip}_s1-2.jsonl; default = sol_<m>_plain; analyse feasible + gap vs
results/h5/ref.json and the per-instance portfolio default + none). flex reference re-run still on CPU (tard re-run done). Older: N14d(a) DONE (minimal edit: job-shop 54/80 vs 30/80). RUNNING 11:36 (now done): N14d(b) reuse of adapted programs (CPU -> results/h5/rd/
n14d_reuse.log), N14c2 more models (queue_s2_n14c2.sh: gpt-oss-20b 8044 GPU1, Qwen3.6 8045 GPU0), N14e tard + flex rungs
(poc/run_jssp_var.py, results/h5/{tard,flex}/, queue_s2_n14e.sh: Qwen3-32B 8042 GPU2, gpt-oss-120b 8046 GPU3; CPU refs -> ref.json;
CPU heavily loaded: check ref statuses, re-run refs when idle if many are not OPTIMAL). FIX_MAP has 2 new rows (N12/N13, N14).
N14 DONE (negative alone), N14b DONE (adapt + new rule's snippet: Qwen3-32B VRPTW 18/24 vs 7/24, p=0.007). N14c started 10:42:
job-shop + release dates (poc/run_jssp_rd.py, results/h5/rd/, queue_s2_n14c.sh: gpt-oss-120b 8043 GPU0, Qwen3-32B 8042 GPU2; CPU ref
-> results/h5/rd/ref.json). Compare feasible rate scratch vs good vs bad (sol_<model>_<cond>_s1-2.jsonl). PROPOSAL restructured by the
writing session 09:53 (R1-R4, M1-M4): numbers in place only. Old note: run_co.py --adapt_from/--adapt_note added; N14 RUNNING since 10:30 (queue_s2_n14.sh, Qwen3-32B 8043 GPU0, Qwen3.6 8042 GPU2) +
queue_s2_n14m2.sh (gpt-oss-20b 8044 GPU1, after sources_S2_N10m2.json). Analyse: optimal rate per (model, dst, condition) over
co_S2_N14_<model>_<dst>_<good|bad|unrel>_s1-3 vs scratch co_<S2_N10|S2_N10m3|S2_N10m2>_co_doc_s1-3 (cvrp/vrptw rows).
N12 replicated (geo + co), N10-M3 done (Qwen3.6 thinking = avoid). CRITIQUE item 4 measured (input tokens). N10-M2 gpt-oss-20b factorial running
(queue_s2_n10m2.sh, 8043 GPU0 geo / 8042 GPU2 co; analyse with N10_PREFIX=S2_N10m2 python poc/analyze_n10.py, also N11=1). N9 replicated
(3 seeds: medium repair = fresh medium; chain not claimed), N9 replication seeds 2-3
(queue_s2_n9r.sh, gpt-oss-120b 8043 GPU0 / 8042 GPU2; analysis poc/analyze_n9.py, extend to seeds). User 10-16 framing: the
project = selecting adequate tools/fixes for problems; N10 is the automatic version of FIX_MAP. RULE (user 10-16): never idle.
Rule learned: positive claims need >= 3 seeds (N6 single-seed p=0.03 did not replicate).

The project now runs on server 2 (host `439b44020469`, 8 × RTX PRO 6000 Blackwell 96 GB; this project uses **GPUs 0–3**). All its
servers are stopped. What was rebuilt and changed:
- Client venv `/root/venvs/llm_algo_poc` (openai, numpy, requests, ortools 9.15.6755, matplotlib): the old hard-coded client path works.
- Serving: vLLM 0.22 in the base conda python (`/opt/conda/bin/python`); `poc/serve_gpu.sh` sets `VLLM_USE_FLASHINFER_SAMPLER=0`
  (needed on Blackwell) and no longer passes `--disable-log-requests` (removed in 0.22). `/dev/shm/pylib_vllm` is not used (set
  `POC_PYLIB` only to use such a dir again). Ports 8040–8049.
- The CIFS copy has no exec bits: call every script as `bash poc/<script>.sh` (start_server.sh does this for serve_gpu.sh).
- Models: everything in `/SSD/huggingface` (Qwen3-1.7B/8B/14B, gpt-oss-20b/120b, Llama-3.1-8B, Llama-3.3-70B w4a16, Gemma-3-27B int4);
  Qwen3-32B-AWQ was downloaded there (the bf16 `Qwen3-32B` is a different model; all 32B numbers are AWQ). R1-Distill-Llama-70B w4a16
  is not on this server.
- Same-stack controls: VRPTW cells re-run on vLLM 0.22 gave exactly the old opt counts (27, 21, 8, 18, 0 of 30); `poc/sanity_check.py`
  480/480 on all 13 geometry tasks.
- Done on server 2 (details in results/FINDINGS.md from "2026-10-13 12:10" on, PROPOSAL.md updated): step 2 (VRPTW `--show_stdin` for
  all gpt-oss settings, Qwen3-32B, Llama-70B), step 3 (figures re-scored packaging-free; Qwen3-1.7B's −35.7 was copy failures), step 4
  (E1 taxonomy, see results/E1_TAXONOMY_DRAFT.md), step 5 (C1 confidence analysis, 8B + 32B), E2 (new tasks delaunay / diameter,
  `results/PREREG_E2.md`), E3 (`results/PREREG_E3.md`), E4 (`results/PREREG_E4_REPLAY.md`), F3x (show stdin in geometry).
- Also done: E2 extension (Llama-70B, Qwen3-14B, thinking 8B/32B on the Delaunay contract test), C1 at 32B.
- Decisions left to the user: (1) TSP checker rejects tours printed with the closing city (`0 … 0`, 281 of 293 such failures are optimal
  tours); PROPOSAL keeps the stated format and reports the lenient re-score as a sensitivity (E1). (2) fig8's "needed helpers only"
  baseline was switched to the matched K0 run (old values 95.0 / 97.0 / 93.3 came from a different header).
- Related work checked per finding (results/RELATED_WORK.md, PROPOSAL §2). Next: run the baselines listed there in priority order
  (label-free selection vs MR-select; forgetting mitigation vs self-replay; helper-context; DRoC), each pre-registered.
  Done 2026-10-13: B1 selection baselines (results/PREREG_B1.md), B2 forgetting baselines (PREREG_B2.md), B3 helper-context baselines
  (PREREG_B3.md: scope sentence, S2A, DRAFT docs), B4 solver-code baselines (PREREG_B4.md: DRoC-style retrieval, restating fields).
  **Correction (F3y): the VRPTW 'skipped field' was an ambiguous header in our prompt (`service horizon`); with `service_time` gpt-oss is
  30/30.** A1 audit (format_audit.py): no other format string is ambiguous; run it for any new task before experiments.
  All planned baselines are done; E4b (large in-task gain) and R1 (second training seed) confirm self-replay. PROPOSAL.md was tightened
  to ≈4.8k words on 2026-10-13 (pre-tightening copies in results/archive/). Next: new experiments only if they address a stated limitation.
  L1 (2026-10-13 23:35): helper steering survives an API-only library framing (32B −19.3); 8B hallucinates missing library functions.
  L2 (2026-10-14 00:35): one 'exactly these functions' sentence stops the hallucinated imports, not the steering.
  Methods (2026-10-14): M1 likelihood filter failed at calibration; M4 algorithm-first wins on steering tasks, loses to think-1024 overall;
  M3 per-helper probe expensive and blind to consistent errors; M2 probe sentence does not help; TroVE-style mode voting strongest.
  M5 (2026-10-14 02:45): M4 draft-vs-rewrite + metamorphic tie-break: 32B 91.5% at 0.8k tokens (frontier), 8B no gain.
  HARDER PROBLEMS (2026-10-14 03:30, user concern 'too easy'): H1 large inputs running (PREREG_H1.md); then H2 CodeContests geometry,
  H3 CVRPLIB/Solomon, H4 gpt-oss-120b medium/high. LLM-generated problems only as a verified pilot (see FINDINGS 03:30).
  STATUS 06:40: H1 done (large inputs still easy for gpt-oss; helper harm doubles), H2 done (31 Codeforces geometry problems hard),
  H2b done (short think budget + examples check is the cheap fix; examples pass many wrong programs), H2c Part A done (MBR-exec
  among passers +3/93, 0 losses). Full set: 355 geometry problems in results/h2/cc_geometry_full.json (shards on /SSD/huggingface/
  datasets_cc, delete after validation); `CC_SET=full python poc/run_cc.py validate|run` -> cc_valid_full.json, cc_full_<tag>_s<seed>.jsonl.
  H2c Part B queued (poc/queue_s2_h2c.sh; 8040 extra Qwen3-32B-AWQ on GPU0 for full thinking).
  H3 (Solomon VRPTW, 56 instances, results/h3, poc/run_solomon.py, PREREG_H3.md): prompt now shows the file's first 12 lines;
  programs mostly crash reading the file -> H3b format-fact arms (--parser) in poc/queue_s2_h3b.sh (old queue_s2_h3.sh stopped).
  Server PIDs: 8040 3180120 Qwen3-32B-AWQ (GPU0), 8042 3070505 gpt-oss-20b (GPU2), 8043 3071062 gpt-oss-120b (GPU3),
  8044 3564475 gpt-oss-120b (GPU1; 8041 Qwen stopped 10:4x). H2c Part B done (full thinking k=1). Methods N1-N4: PREREG_N.md.
  Done: H3b/H3c, N2b, N4, H4 (helpers on real problems), FM (fact mining; verification by feasibility hurt).
  FM2 replicated: mean 32.5% over six chains (D 64.6% was the outlier); no help for 20b. H5 job-shop done (79-85%, no facts
  needed). SANDBOX FIX 15:3x: run_python(cpu_s=...) - RLIMIT_CPU = timeout killed multi-threaded CP-SAT ('tle' in 2-11 s);
  pass cpu_s for any multi-threaded solver. FM3 done: fact mining CLOSED as partial negative (PREREG_FM.md).
  H4b done. PROPOSAL restructured: Section 4.4 Hard benchmarks + figs 9-11 (poc/make_figures_hard.py).
  Methods (PREREG_V.md): V1 reuse works when a candidate exists; V2/V3, N5, N6 closed (N6 seed-1 p=0.03 did not replicate).
  Done: V1-JSSP (100%), D1 (teacher programs hurt; self data +2.3 on clean split), H6c. NOTE: 37 CodeContests statements are
  duplicated (Div1/Div2 copies); D1 uses a clean 88-problem test split. D1 arm E done (comments do not undo the harm).
  Distillation D1-D3 CLOSED (teacher programs hurt, own data neutral). V1G done (reuse removes F1 harm with 5 labelled checks).
  V1A done (label-free reuse only where the model can write the oracle); V1G-tb: labelled checks + agreement tie-break -> 100%.
  H6d done. PROPOSAL condensed to ~5.5k words, methods in one table in 4.4 (backups results/archive/*_before_condense_2026-10-15.md).
  N2m done (+4.8/+2.3/+0.6 per round). V1c done 09:3x (cost curve, fig12). Earlier: V1c (queue_s2_v1c.sh: Qwen3-32B-AWQ 8041 GPU0 mining candidates;
  CPU poc/analyze_reuse_curve.py -> results/h3/reuse_curve.log, cache results/h3/cand_eval_<arm>.json).
- Open: E5 (closed API model; no API access here); PROPOSAL_ko.md must mirror every PROPOSAL.md change (synced 13:55 UTC).

## 1. What to copy

Copy the whole project folder (`/NAS/SJ/POSTECH/nlp`, about 275 MB):

| path | contents |
|---|---|
| `PROPOSAL.md`, `PROPOSAL_ko.md` | the single project document (English / Korean mirror, kept in sync) |
| `results/FINDINGS.md` | full chronological log (~2.3k lines); the latest entries are at the end |
| `results/*.jsonl` | raw outputs of every run (prompts, programs, classes, tokens); needed for any re-analysis |
| `results/PREREG_E4.md` | pre-registration for E4 |
| `results/archive/` | old long versions of the proposal; `partial_stopped/` = runs killed mid-way (discard) |
| `poc/` | all code (harness, generators, references, analysis, queue scripts) |
| `figs/` | figures used in the proposal |

## 2. Environment to rebuild

- **Client / harness** (CPU): Python ≥ 3.10 venv with `openai numpy requests ortools==9.15.6755 matplotlib` (see `poc/requirements.txt`). OR-Tools must be importable by the sandboxed program runner (`poc/sandbox.py` runs generated code with the same interpreter).
- **Serving**: vLLM 0.10.2 (torch 2.8, transformers 4.57.1) with an OpenAI-compatible API; `poc/serve_gpu.sh` / `poc/start_server.sh` start one server per GPU. gpt-oss needs vLLM ≥ 0.10.1.
- **Distillation (F5/E4)**: torch + transformers + peft on a GPU (`poc/sft_lora.py`).
- **Models used**: Qwen3-1.7B / 8B / 14B / 32B-AWQ, Llama-3.1-8B-Instruct, Llama-3.3-70B-Instruct w4a16, DeepSeek-R1-Distill-Llama-70B w4a16, Gemma-3-27B int4, gpt-oss-20b / 120b.
- **Hard-coded paths to replace** (`grep -rl` over `poc/`): `/NAS/SJ/POSTECH/nlp` (project root, ~150 places), `/root/venvs/llm_algo_poc/bin/python` (client python, ~150, mostly queue scripts), `/SSD/huggingface/...` (model dirs), `/dev/shm/pylib_vllm` and `/opt/conda/bin/python` (vLLM / SFT python). Replacing them with environment variables once is worth it.
- Client env vars: `POC_BASE_URL` (e.g. `http://127.0.0.1:8040/v1`), `POC_REASONING_EFFORT` (gpt-oss only: low / medium / high).

## 3. Prompt for the new session

Paste the block below into the new Claude Code session (adjust the paths in the first paragraph).

````text
You are continuing a graduate NLP course team project: "LLMs for computational geometry (CG) and combinatorial
optimization (CO)": when LLM-written geometry / optimization programs fail, why, and which cheap fix to use.
Scope is CG + CO only (user decision). The project folder is <PROJECT_ROOT> (copied from the old servers).

Read first, in this order:
1. HANDOFF.md (environment, hard-coded paths, what to copy).
2. PROPOSAL.md: the single project document (problem, why LLMs write programs, setup, findings F1-F5 with real
   examples, planned E1-E5, limitations, how to run). PROPOSAL_ko.md is its Korean mirror; keep both in sync.
3. The last ~300 lines of results/FINDINGS.md (full chronological log; finals at the end).

What is established (details and numbers in PROPOSAL.md):
- Geometry: 8 metamorphic variants per instance (identity, translate, rot90, mirror, permute, scale, 1e9 offset,
  degenerate); a program counts as correct only if right on all 8. The same check, label-free, selects among samples
  (MR-select).
- F1: extra helper functions in the prompt steer the algorithm choice (convex hull: monotone chain -> Graham on the
  offered polar_sort, wrong on degenerate cases). Thinking fixes it at ~15k tokens; a one-sentence algorithm hint at ~0.6k.
- F2: a needed helper with a hidden contract (signed area without abs) is a trap.
- F3: solver code fails on missing API facts; only the exact OR-Tools snippet fixes it (near-miss docs = no docs).
  Newest: on VRPTW, gpt-oss-120b skips the stated `service` field in the input header (0-3/30 programs read it);
  re-running its programs with that field removed makes 43/49 optimal. Showing the instance's literal stdin in the
  prompt (run_co.py --show_stdin) takes gpt-oss-20b low from .07-.17 to .87-.97 (best-of-3 1.00) at half the tokens.
- F4: pick the fix by error type: random slips -> sampling + metamorphic check; systematic errors -> hint/thinking;
  they compose (clipping: gpt-oss-20b low 14 -> 59/60 with hint + 3 samples + check).
- F5: LoRA distillation of verified thinking programs into the no-thinking 8B works per task, damages other tasks (LOTO).

Next steps, in priority order:
1. Rebuild the environment (HANDOFF.md section 2), fix hard-coded paths, run poc/sanity_check.py (every geometry
   reference must pass through the harness), then reproduce one known number before any new run, e.g.
   `run_co.py --model_tag W_cooss20low_doctask_ex_s1 --arms solver --probs vrptw --n_inst 15 --repair 2
   --temperature 0.7 --max_tokens 16000 --show_stdin --api_doc --api_doc_task --seed 1` with gpt-oss-20b at low
   effort should give about 27/30 optimal.
2. Finish the --show_stdin test: gpt-oss-120b low/medium and Qwen3-32B (template: poc/queue_vrptw3.sh; it waits on an old-server PID and uses old GPU ids, edit before use).
3. Regenerate fig2 / fig7 with the packaging-free numbers (poc/make_figures.py; see FINDINGS on rescore_prelude.py).
4. E1 failure taxonomy over all stored programs (CPU only): API/knowledge, input format, logic, orientation,
   degenerate case; per model and condition.
5. Confidence analysis: do token log-probs of a program predict correctness (a label-free selector to compare with
   MR-select)? poc/logit_probe2.py has the teacher-forced prompt_logprobs machinery.
6. E2-E4 as planned in PROPOSAL.md section 4.3 (pre-registered new tasks, deployable pipeline, distillation with replay).

Working rules learned the hard way:
- Treat surprising numbers as harness bugs until the raw outputs say otherwise: read the programs and error messages,
  compare against a reference program run through the same harness. Past bugs: non-simple polygons, brute-force
  checker errors, NameError from copied helper packaging (inflated "neutral header harm"), a doubled ```python fence
  making gpt-oss look like it wrote no code (fixed in llm.py last_block). Report fixes vs. findings separately.
- Every claim in PROPOSAL.md needs a number from results/ and, for examples, a real stored output.
- Record every finished run in results/FINDINGS.md (append; date/time heading), then update PROPOSAL.md and
  PROPOSAL_ko.md. Keep PROPOSAL.md short: only findings that matter for the project.
- GPUs may be shared: check nvidia-smi before starting a server, cap --gpu-memory-utilization to what is free,
  leave headroom for other users, log choices in results/gpu_choice.log, and shut servers down when no run uses them.
  Queue scripts must wait on specific PIDs (`while kill -0 $PID`), never a bare `wait` on unrelated children.
- vLLM binds with SO_REUSEPORT: a second server on a busy port "starts" and requests get split between two models.
  start_server.sh refuses a port that already answers; keep one port range per session.
- Never `pkill -f` a pattern that can match your own shell; kill by PID.
- If the project lives on a CIFS/NAS mount: `sed -i` and in-place editors can delete files there; rewrite files
  with Python instead.
````
