#!/bin/bash
# HO6 (docs/prereg/PREREG_HO.md): one cheap repair with the failure evidence for the escalated freev programs on BWOR / LogiOR, seeds 1-3.
#   sbatch -J ho6_q8b poc/slurm/job.sh poc/slurm/ho6_lane.sh Qwen/Qwen3-8B q8b ''   (gpt-oss: ... oss20 low)
dir=$1 m=$2 effort=$3
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 ho6_$m --max-model-len 20480) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_TIMEOUT=7200
[ -n "$effort" ] && export POC_REASONING_EFFORT=$effort
for set in bwor logior; do for sd in 1 2 3; do
  NLOPT_SET=$set $P poc/run_repair.py $m $sd >> results/x3/run_ho6_$m.log 2>&1 &
done; done; wait
kill $S; sleep 15
echo "SL_HO6 $m done $(date -u)" >> results/queue_log.txt
