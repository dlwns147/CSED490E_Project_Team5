#!/bin/bash
# E1: family vs capability for the distractor harm — Llama-3.1-8B, K=0 vs K=8 related helpers, n=300, --stdlib, T=0.7, seeds 1-2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8082 llama8_dis 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8082/v1; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
for sd in 1 2; do for k in 0 8; do $P poc/run_geo_cross.py --model_tag X_geoxllama8_dis${k}_t07s$sd $X --seed $sd --distract $k > results/run_X_geoxllama8_dis${k}_s$sd.log 2>&1; done; done
kill $S
echo L8DIS_DONE >> results/queue_log.txt
