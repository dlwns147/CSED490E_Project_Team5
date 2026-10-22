#!/bin/bash
# HO-G-R (docs/prereg/PREREG_HOGC.md, addendum): one cheap repair on a visible failure of the held-out geometry fact programs, seeds 1-3,
# the three models one after another (few items per model).   sbatch -J hogr poc/slurm/job.sh poc/slurm/hogr_lane.sh
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for spec in "Qwen/Qwen3-8B q8b" "Qwen/Qwen3-14B-AWQ q14a" "openai/gpt-oss-20b oss20 low"; do
  set -- $spec; dir=$1 m=$2
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 hogr_$m --max-model-len 20480) || { echo "$m: server failed"; continue; }
  if [ -n "$3" ]; then export POC_REASONING_EFFORT=$3; else unset POC_REASONING_EFFORT; fi
  for sd in 1 2 3; do $P poc/run_geo_repair.py $m $sd >> results/run_SL_HOGR_$m.log 2>&1; done
  kill $S; sleep 15
  echo "SL_HOGR $m done $(date -u)" >> results/queue_log.txt
done
