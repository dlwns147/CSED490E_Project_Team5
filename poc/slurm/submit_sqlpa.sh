#!/bin/bash
# SQL-PA runs (docs/prereg/PREREG_SQL.md, addendum SQL-PA): SQL-1's arms on the fresh BIRD-train questions ($POC_DATA/bird/pa_ids.txt)
# for Qwen3-8B (TP 2), Qwen3-14B-AWQ and Qwen3.5-9B (two shards each), seeds 1-3, with SQL-1's commands; Nemotron-3-Nano (4 x 3090,
# TP 4) runs the cheap arm only, on the fresh questions (n3npa) and on dev (n3n), all six runs against one server.
cd "$(dirname "$0")/../.."
X="SQL_SPLIT=train SQL_IDS=/NAS/SJ/POSTECH/nlp_data/bird/pa_ids.txt"
for s in 1 2 3; do
  for j in 0 1; do
    sbatch -J sqlpa_q35_p${j}_s$s -x n19,n22 poc/slurm/job.sh "S=\$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.5-9B \$PORT 0 0.92 sqlpa_q35_p${j}_s$s --max-model-len 24576 --language-model-only --max-num-seqs 32) || exit 1; export POC_BASE_URL=http://127.0.0.1:\$PORT/v1 POC_TIMEOUT=7200 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5 POC_BUDGET_CARD=1; $X SQL_SUBSET=$j/2 \$P poc/run_sql.py q35pap$j $s >> results/sql/run_q35pap${j}_$s.log 2>&1; kill \$S"
    sbatch -J sqlpa_q14a_p${j}_s$s -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 24576' Qwen/Qwen3-14B-AWQ sqlpa_q14a_p${j}_s$s \
      "$X SQL_SUBSET=$j/2 \$P poc/run_sql.py q14apap$j $s >> results/sql/run_q14apap${j}_$s.log 2>&1"
  done
  sbatch -J sqlpa_q8b_s$s -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --gpus 0,1 --vllm '--max-model-len 24576 --tensor-parallel-size 2' Qwen/Qwen3-8B sqlpa_q8b_s$s \
    "$X \$P poc/run_sql.py q8bpa $s >> results/sql/run_q8bpa_$s.log 2>&1"
done
C=()
for s in 1 2 3; do
  C+=("$X SQL_ARMS=cheap \$P poc/run_sql.py n3npa $s >> results/sql/run_n3npa_$s.log 2>&1" "SQL_ARMS=cheap \$P poc/run_sql.py n3n $s >> results/sql/run_n3n_$s.log 2>&1")
done
sbatch -J sqlpa_n3n -x n19,n22 --gres=gpu:4 --cpus-per-task=16 poc/slurm/job.sh poc/slurm/n3n_lane.sh sqlpa_n3n "${C[@]}"
