#!/bin/bash
# SQL-FA runs (docs/prereg/PREREG_SQL.md, addendum SQL-FA): per model / shard / seed, the fact (card + library) with the library
# admitted by agreement with the short think (g), by gold as right (r) or wrong (w); arms N and T, the three in parallel against one
# server. Low priority (--nice), behind CV-1.
cd "$(dirname "$0")/../.."
for s in 1 2 3; do
  for j in 0 1; do
    sbatch --nice=200 -J sqlfa_q14a_p${j}_s$s -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 24576' Qwen/Qwen3-14B-AWQ sqlfa_q14a_p${j}_s$s \
      "SQL_LIB=q14a SQL_SUBSET=$j/2 SQL_FACT=both SQL_ARMS=cheap,think SQL_LIB_ADMIT=agree \$P poc/run_sql.py q14afgp$j $s >> results/sql/run_q14afgp${j}_$s.log 2>&1" \
      "SQL_LIB=q14a SQL_SUBSET=$j/2 SQL_FACT=both SQL_ARMS=cheap,think SQL_LIB_ADMIT=right \$P poc/run_sql.py q14afrp$j $s >> results/sql/run_q14afrp${j}_$s.log 2>&1" \
      "SQL_LIB=q14a SQL_SUBSET=$j/2 SQL_FACT=both SQL_ARMS=cheap,think SQL_LIB_ADMIT=wrong \$P poc/run_sql.py q14afwp$j $s >> results/sql/run_q14afwp${j}_$s.log 2>&1"
  done
  sbatch --nice=200 -J sqlfa_q8b_s$s -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --gpus 0,1 --vllm '--max-model-len 24576 --tensor-parallel-size 2' Qwen/Qwen3-8B sqlfa_q8b_s$s \
    "SQL_LIB=q8b SQL_FACT=both SQL_ARMS=cheap,think SQL_LIB_ADMIT=agree \$P poc/run_sql.py q8bfg $s >> results/sql/run_q8bfg_$s.log 2>&1" \
    "SQL_LIB=q8b SQL_FACT=both SQL_ARMS=cheap,think SQL_LIB_ADMIT=right \$P poc/run_sql.py q8bfr $s >> results/sql/run_q8bfr_$s.log 2>&1" \
    "SQL_LIB=q8b SQL_FACT=both SQL_ARMS=cheap,think SQL_LIB_ADMIT=wrong \$P poc/run_sql.py q8bfw $s >> results/sql/run_q8bfw_$s.log 2>&1"
done
