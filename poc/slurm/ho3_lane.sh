#!/bin/bash
# HO3 (docs/prereg/PREREG_HO.md): per model, the freev cheap programs (solution printed) on BWOR / LogiOR, seeds 1-3, then the solution
# checkers for them (poc/run_verify.py); one server for both phases.
#   sbatch -J ho3_q8b poc/slurm/job.sh poc/slurm/ho3_lane.sh Qwen/Qwen3-8B q8b [low]
dir=$1 m=$2 effort=$3
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 ho3_$m --max-model-len 20480) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_TIMEOUT=7200
[ -n "$effort" ] && export POC_REASONING_EFFORT=$effort
for set in ${HO3_SETS:-bwor logior}; do for sd in 1 2 3; do
  NLOPT_SET=$set $P poc/run_nlopt.py ${m}_$set freev $sd --max_tokens 8192 >> results/x3/run_ho3_$m.log 2>&1 &
done; done; wait
for set in ${HO3_SETS:-bwor logior}; do for sd in 1 2 3; do
  NLOPT_SET=$set $P poc/run_verify.py $m $sd >> results/x3/run_ho3_$m.log 2>&1 &
done; done; wait
kill $S; sleep 15
echo "SL_HO3 $m done $(date -u)" >> results/queue_log.txt
