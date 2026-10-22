#!/bin/bash
# HO7 (docs/prereg/PREREG_HO.md): one cheap repair on a visible failure (no checker): OptiBench with the library (formx) and OptMATH (free),
# seeds 1-3, one model per job.   sbatch -J ho7_q8b poc/slurm/job.sh poc/slurm/ho7_lane.sh Qwen/Qwen3-8B q8b ''   (gpt-oss: ... oss20 low)
dir=$1 m=$2 effort=$3
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 ho7_$m --max-model-len 20480) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_TIMEOUT=7200
[ -n "$effort" ] && export POC_REASONING_EFFORT=$effort
for sd in 1 2 3; do
  NLOPT_SET=optibench $P poc/run_repair.py $m $sd formx >> results/x3/run_ho7_$m.log 2>&1 &
  NLOPT_SET=optmath $P poc/run_repair.py $m $sd free >> results/x3/run_ho7_$m.log 2>&1 &
done; wait
kill $S; sleep 15
echo "SL_HO7 $m done $(date -u)" >> results/queue_log.txt
