# Prompt for the Claude Code session on the Slurm server

Paste the block below as the first message of a new Claude Code session started in the cloned repository.

```text
Continue the POSTECH graduate NLP class project "Tools, Facts, and Checks" (CSED490E, team 5) on this Slurm cluster. The repository is
github.com/dlwns147/CSED490E_Project_Team5 (public, branch main); it was moved here from another server on 2026-10-20.

Read first, in this order: docs/SLURM_HANDOFF.md (state, evidence table, next steps, data/model paths, environment, how runs map to Slurm,
harness traps, working rules), then PROPOSAL.md, the tail of docs/FINDINGS.md, docs/prereg/PREREG_HOG.md and docs/prereg/PREREG_HO.md.

Scope: computational geometry and combinatorial optimization solved by LLM-written programs, accurately and cheaply, with models that fit
one 24 GB GPU (gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B; larger models only as references). Every result reports accuracy together with tokens.

Setup before any experiment:
1. Find the cluster's partitions, GPU types, time limits and storage with sinfo / squeue / scontrol and the site docs; ask me for the account,
   partition or quota if they are not discoverable. Never run GPU work on the login node.
2. Recreate the environment of docs/SLURM_HANDOFF.md §5 (vLLM 0.22 server env; client/sandbox env with openai, ortools, coptpy, numpy,
   sympy, math-verify, cvxpy, scipy). Point the hard-coded data paths (run_nlopt.MAMO / OPTMATH / OPTIBENCH, Lean, AlphaGeometry) to where the
   data lives here, and download the models listed in §4 to a shared models directory (check free space first).
3. Ask me whether to copy the raw results (results/*.jsonl, ~2 GB, not in git) from the old server; analyses need them, new runs do not.
4. Smoke test with one short sbatch job: serve Qwen3-8B with poc/start_server.sh, run 10 OptiBench problems with
   `NLOPT_SET=optibench python poc/run_nlopt.py q8b_optibench free 1`, read the raw programs, and check that accuracy and tokens are in the
   range of the old runs (docs/prereg/PREREG_HO.md). Write a reusable sbatch template under poc/slurm/ and commit it.

Then continue with docs/SLURM_HANDOFF.md §3, most important first: (1) close the check leak that makes the recipe fail for Qwen3-8B on the
held-out geometry tasks (a label-free differential check, e.g. a brute-force program on small random inputs), (2) a label-free signal for
when a fact does NOT pay, (3) fold the held-out results into the final report.

Rules (mine, standing): pre-register predictions with numbers and a decision rule in docs/prereg/PREREG_*.md before running; at least 3 seeds
for any positive claim; report cost-accuracy, not accuracy alone; read raw programs and treat surprising numbers as harness bugs until the raw
outputs say otherwise; append dated entries to docs/FINDINGS.md; update PROPOSAL.md and its Korean mirror PROPOSAL_ko.md together, short,
numbers edited in place; do not edit the slide files unless I ask; commit and push after each change (public repo: scan the staged diff for
secrets, never commit raw outputs); before starting any run, ask whether it can change the project's main claim, and skip it if not — no
replications or baselines for their own sake. Explain results to me for a first-time reader: what ran, how, the result with its cost, what
is next.
```
