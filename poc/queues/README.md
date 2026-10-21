# Queue scripts (old servers)

Each `queue_*.sh` here is the exact record of how an experiment ran on the old servers (up to 2026-10-20): which model, arms, seeds,
token budgets and effort levels. They are kept unchanged because the pre-registrations and FINDINGS entries cite them.

**Do not run them as they are on the Slurm cluster.** They start several model servers at once on GPUs 0–3 of one shared machine
and claim a GPU with `mkdir results/.gpu_claim_<g>`; two Slurm jobs would share those lock directories through the repository, and a
job sees only its own GPU (index 0).

To repeat a lane on Slurm, give its model and client commands to `poc/slurm/lane.sh` (one job = one server + its clients):

```bash
# from queue_s2_ob.sh, lane "Qwen/Qwen3-8B q8b", seed 1:
sbatch -J ob_q8b poc/slurm/job.sh poc/slurm/lane.sh Qwen/Qwen3-8B ob_q8b \
  'NLOPT_SET=optibench POC_TIMEOUT=7200 $P poc/run_nlopt.py q8b_optibench free 1 --max_tokens 8192' \
  'NLOPT_SET=optibench POC_TIMEOUT=7200 $P poc/run_nlopt.py q8b_optibench thinkfree 1 --think --max_tokens 16000'
```

or, for the standard arms of `bench.py`, `python bench.py submit <bench> <arm> --model <alias> --seeds 1,2,3 [--dry]`.
Paths inside the container are the old ones (`/NAS/SJ/POSTECH/nlp`, `/SSD/huggingface`, `/root/venvs/llm_algo_poc`), so the client
commands can be copied unchanged. On a 3090 keep thinking budgets ≤ 16k tokens (the lane serves `--max-model-len 20480`); runs with
larger budgets (contest high effort 62k, Qwen3.6 80k) need a larger GPU. Experiments started on Slurm have their lane scripts in
`poc/slurm/` (e.g. `hogc_brute.sh`).
