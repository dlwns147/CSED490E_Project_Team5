#!/bin/bash
# HO-G-C (docs/prereg/PREREG_HOGC.md): brute-force programs for the four held-out geometry tasks, seeds 1-3, one model per job.
#   sbatch -J hogc_q8b poc/slurm/job.sh poc/slurm/hogc_brute.sh Qwen/Qwen3-8B q8b
#   sbatch -J hogc_oss20 poc/slurm/job.sh poc/slurm/hogc_brute.sh openai/gpt-oss-20b oss20 low
dir=$1 m=$2 effort=$3
GX="--stdlib --n_inst 12 --temperature 0.7 --tasks overlap,convex,tri,clip --resume"
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 hogc_$m --max-model-len 20480) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
[ -n "$effort" ] && export POC_REASONING_EFFORT=$effort
for sd in 1 2 3; do
  t=SL_HOGC_${m}_geo_brute_s$sd
  $P poc/run_geo_cross.py --model_tag $t $GX --seed $sd --brute --max_tokens 4096 >> results/run_$t.log 2>&1 &
done; wait
kill $S; sleep 15
echo "SL_HOGC $m done $(date -u)" >> results/queue_log.txt
