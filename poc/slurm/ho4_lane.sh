#!/bin/bash
# HO4 (docs/prereg/PREREG_HO.md): OptiBench, the library arm with the solution printed (formxv), then the solution checkers for it; one model,
# one seed per job.   sbatch -J ho4_q8b_s1 poc/slurm/job.sh poc/slurm/ho4_lane.sh Qwen/Qwen3-8B q8b 1 [low]
dir=$1 m=$2 sd=$3 effort=$4
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 ho4_${m}_s$sd --max-model-len 20480) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_TIMEOUT=7200 NLOPT_SET=optibench
[ -n "$effort" ] && export POC_REASONING_EFFORT=$effort
$P poc/run_form.py $m formxv $sd >> results/x3/run_ho4_${m}_s$sd.log 2>&1
$P poc/run_verify.py $m $sd formxv >> results/x3/run_ho4_${m}_s$sd.log 2>&1
kill $S; sleep 15
echo "SL_HO4 $m s$sd done $(date -u)" >> results/queue_log.txt
