#!/bin/bash
# SQL-F full runs (docs/prereg/PREREG_SQL.md, addendum SQL-F): per model / shard / seed, card-only and library-only cheap arms and the
# fact (both) on all arms, in parallel against one server.
cd "$(dirname "$0")/../.."
for s in 1 2 3; do
  for j in 0 1; do
    sbatch -J sqlf_q35_p${j}_s$s -x n19,n22 poc/slurm/job.sh "S=\$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.5-9B \$PORT 0 0.92 sqlf_q35_p${j}_s$s --max-model-len 24576 --language-model-only --max-num-seqs 32) || exit 1; export POC_BASE_URL=http://127.0.0.1:\$PORT/v1 POC_TIMEOUT=7200 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5 POC_BUDGET_CARD=1 SQL_LIB=q35 SQL_SUBSET=$j/2; SQL_FACT=card SQL_ARMS=cheap \$P poc/run_sql.py q35cp$j $s >> results/sql/run_q35cp${j}_$s.log 2>&1 & SQL_FACT=lib SQL_ARMS=cheap \$P poc/run_sql.py q35lp$j $s >> results/sql/run_q35lp${j}_$s.log 2>&1 & SQL_FACT=both \$P poc/run_sql.py q35fp$j $s >> results/sql/run_q35fp${j}_$s.log 2>&1; wait; kill \$S"
    sbatch -J sqlf_q14a_p${j}_s$s -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 24576' Qwen/Qwen3-14B-AWQ sqlf_q14a_p${j}_s$s \
      "SQL_LIB=q14a SQL_SUBSET=$j/2 SQL_FACT=card SQL_ARMS=cheap \$P poc/run_sql.py q14acp$j $s >> results/sql/run_q14acp${j}_$s.log 2>&1" \
      "SQL_LIB=q14a SQL_SUBSET=$j/2 SQL_FACT=lib SQL_ARMS=cheap \$P poc/run_sql.py q14alp$j $s >> results/sql/run_q14alp${j}_$s.log 2>&1" \
      "SQL_LIB=q14a SQL_SUBSET=$j/2 SQL_FACT=both \$P poc/run_sql.py q14afp$j $s >> results/sql/run_q14afp${j}_$s.log 2>&1"
  done
  sbatch -J sqlf_q8b_s$s -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --gpus 0,1 --vllm '--max-model-len 24576 --tensor-parallel-size 2' Qwen/Qwen3-8B sqlf_q8b_s$s \
    "SQL_LIB=q8b SQL_FACT=card SQL_ARMS=cheap \$P poc/run_sql.py q8bc $s >> results/sql/run_q8bc_$s.log 2>&1" \
    "SQL_LIB=q8b SQL_FACT=lib SQL_ARMS=cheap \$P poc/run_sql.py q8bl $s >> results/sql/run_q8bl_$s.log 2>&1" \
    "SQL_LIB=q8b SQL_FACT=both \$P poc/run_sql.py q8bf $s >> results/sql/run_q8bf_$s.log 2>&1"
done
