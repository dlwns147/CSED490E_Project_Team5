#!/bin/bash
# E4b base reference: Qwen3-8B convex K0/K8 seeds 1-2 on 8040 (GPU 0).
cd /NAS/SJ/POSTECH/nlp
export POC_BASE_URL=http://127.0.0.1:8040/v1
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --tasks convex"
for k in 0 8; do for sd in 1 2; do
  /root/venvs/llm_algo_poc/bin/python poc/run_geo_cross.py --model_tag S2_E4b_base_convex_k${k}_s$sd $X --seed $sd --distract $k > results/run_S2_E4b_base_k${k}_s$sd.log 2>&1 &
done; done
wait
echo "S2_E4b base done $(date)" >> results/queue_log.txt
