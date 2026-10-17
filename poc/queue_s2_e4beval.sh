#!/bin/bash
# E4b eval of one merged model: convex K0/K8 s1-2 (unseen) + 5 core tasks K8 s1. usage: bash poc/queue_s2_e4beval.sh <arm> <port> <gpu> [frac]
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
arm=$1 port=$2 gpu=$3
S=$(bash poc/start_server.sh /dev/shm/e4b_$arm $port $gpu ${4:-0.45} e4b_$arm) || { echo "e4b eval $arm: server failed $(date)" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:$port/v1
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
for k in 0 8; do for sd in 1 2; do
  $P poc/run_geo_cross.py --model_tag S2_E4b_${arm}_convex_k${k}_s$sd $X --tasks convex --seed $sd --distract $k > results/run_S2_E4b_${arm}_convex_k${k}_s$sd.log 2>&1 &
done; done
$P poc/run_geo_cross.py --model_tag S2_E4b_${arm}_core_k8_s1 $X --seed 1 --distract 8 > results/run_S2_E4b_${arm}_core_k8_s1.log 2>&1 &
wait
kill $S
echo "S2_E4b eval $arm done $(date)" >> results/queue_log.txt
