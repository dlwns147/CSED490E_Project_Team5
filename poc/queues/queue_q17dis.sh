#!/bin/bash
# Capability curve, low end: Qwen3-1.7B K=0 vs K=8 related helpers, no-think (n=300, s1) and thinking (n=100, s1); --stdlib, T=0.7.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-1.7B 8088 q17_dis 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8088/v1
for k in 0 8; do $P poc/run_geo_cross.py --model_tag X_geox1_7b_dis${k}_t07s1 --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1 --distract $k > results/run_X_geox1_7b_dis${k}.log 2>&1; done
for k in 0 8; do $P poc/run_geo_cross.py --model_tag T_geox1_7b_dis${k}_s1 --stdlib --think --max_tokens 20000 --temperature 0.7 --seed 1 --distract $k > results/run_T_geox1_7b_dis${k}.log 2>&1; done
kill $S
echo Q17DIS_DONE >> results/queue_log.txt
