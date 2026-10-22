#!/bin/bash
# HO-G-E (docs/prereg/PREREG_HOGC.md, addendum): edge-case tests written once per task by each 24 GB model, seeds 1-3 (one job, the three
# servers one after another; each writes 4 tasks x 3 seeds = 12 short replies).   sbatch -J hogce poc/slurm/job.sh poc/slurm/hogce_tests.sh
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for spec in "Qwen/Qwen3-8B q8b" "Qwen/Qwen3-14B-AWQ q14a" "openai/gpt-oss-20b oss20 low"; do
  set -- $spec; dir=$1 m=$2
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 hogce_$m --max-model-len 20480) || { echo "$m: server failed"; continue; }
  if [ -n "$3" ]; then export POC_REASONING_EFFORT=$3; else unset POC_REASONING_EFFORT; fi
  for sd in 1 2 3; do $P poc/run_edge_tests.py --model_tag SL_HOGCE_${m}_s$sd --seed $sd >> results/run_SL_HOGCE_$m.log 2>&1 & done; wait
  kill $S; sleep 15
  echo "SL_HOGCE $m done $(date -u)" >> results/queue_log.txt
done
