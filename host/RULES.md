# Working rules for the NLP course session (replaces host/LOOP.md, removed 2026-11-25 15:15 UTC by the user; old text: host/LOOP_history.txt)

No loop: no /loop, no ScheduleWakeup, no cron, no per-tick file edits. Work follows the user's messages, the active goal and background-task
notifications. With jobs running, progress is checked about every 30 minutes (user's goal of 11-26 18:17 UTC; a background timer task, not a loop); a check with nothing new is not recorded anywhere.

## Goal (set with /goal by the user, 2026-11-26 18:17 UTC, rules added 18:18 and 18:27 UTC; kept for another 24 hours by the user at 2026-11-27 19:04 UTC ("keep the goal"), so the current window runs 2026-11-27 19:04 UTC + 24 h)
1. Suggest and test novel solutions for various proper math computation problems (since 11-26 16:2x the method target is choosing between disagreeing tool attempts with a computed check, on sets where that room exists: Project Euler, MathConstruct, OEIS; competition answers and word problems stay as measured baselines and scope limits).
2. Suggest and test proof parts; set the boundary for the teammate (computational algorithms, no LLM background; has Codex and Slurm).
Set proper recent research as baselines, measure them, compare with ours. Check recent related research to suggest ideas, check novelty, set baselines. Constructive criticism. Do not suggest heuristic, easy or incremental things (added in the goal re-set of 11-26 18:18 UTC). Check progress every 30 minutes. Never read results by accuracy alone: analyse tokens, logits (log-probabilities, stored from the next new run on), tool calls, timeouts, finish reasons and the generated text itself (rule added 18:27 UTC 11-26). Clean up GPU memory, storage and temporary things when gs15 jobs finish.
Utility = 100·correct − 0.5·ktok (output tokens). Accuracy and tokens are reported separately; wins on both are claims, trade-offs carry their break-even price.

## User rules
- Math computation only, all sets; no puzzles. Any models, specialists included.
- Decide and act; do not end a turn asking. Keep the task as asked; say in one sentence if a better approach exists.
- Records: docs/prereg/*.md and docs/FINDINGS.md (git); proof part only in host/PROOF.md and host/proof/ (never in git). Never edit docs/progress/**, paper/**, or other sessions' files.
- Git: dlwns147 only, no Claude co-author; stage named files only; no raw results, IPs, server names, keys, nlp_data.
- GPUs: gs15 6–7; Slurm RTXPro6000 / RTX3090. CPU work: Slurm CPU partitions with -q nogpu --gres=none --cpus-per-task=4 --mem=40G. Login node: light work only.
- Exact-PID / job-id kills. No foreground sleep. Times copied from date -u. Every background wait has a timeout and tests a line that cannot match its own command (pgrep -f matches its own shell).
- gs15 cleanup (user 11-25 15:3x: "clean up gpu memorys, storage or other temporal things when you finish jobs in GS15"): when a lane ends, its server is stopped, its GPU shows ~0 MiB, its model copy under /root/.cache/models and any temporary file are gone; check and say so in the report. Only this session's processes and files.
- Jobs remove their temporary files in code; running scripts are never edited in place.

## Standards that keep mattering (each from a mistake made here)
- Register hypothesis, prediction and falsifier before the first row; search recent work by mechanism (2–3 phrasings) first; grep the record for the idea first.
- A method must be new against named prior work and not a tuning trick; confirmation, repair prompts, gates and more samples are not new methods.
- Include the cheapest competitor, a zero-token environment fix among them. Inspect any arm that scores exactly 0.
- Same problems, seeds, reader and scorer (run_nlopt.correct) for every arm; baselines get the same aids and the same failure census. Bootstrap by problem.
- Read the status from a run, never from a code pattern. Zero-token rows are failed requests, not answers. "Cannot load" needs the traceback.
- A gain from "the other sample prints a value" needs a census of the missing values first.
- Choose on development data only; the decisive set is fresh. Every number names its script and file.
- A checker's rules are the registered ones: audit the scorer against the registration before scoring (11-25: the T2 check script accepted native_decide).
