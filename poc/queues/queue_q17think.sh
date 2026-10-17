#!/bin/bash
# Tighten the wide CI for Qwen3-1.7B thinking (K=0 vs 8): seeds 2-3, n=100 each, --stdlib, T=0.7.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-1.7B 8089 q17_think 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8089/v1
for sd in 2 3; do for k in 0 8; do $P poc/run_geo_cross.py --model_tag T_geox1_7b_dis${k}_s$sd --stdlib --think --max_tokens 20000 --temperature 0.7 --seed $sd --distract $k > results/run_T_geox1_7b_dis${k}_s$sd.log 2>&1; done; done
kill $S
echo Q17THINK_DONE >> results/queue_log.txt
