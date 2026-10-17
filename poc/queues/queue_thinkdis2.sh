#!/bin/bash
# Firm up "thinking removes the plausible-helper harm": Qwen3-8B thinking K=0/8 (s1, s2) and 14B/32B thinking seed 2; n=100, --stdlib, T=0.7.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
X="--stdlib --think --max_tokens 20000 --temperature 0.7"
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8085 q8b_tdis); export POC_BASE_URL=http://127.0.0.1:8085/v1
  for sd in 1 2; do for k in 0 8; do $P poc/run_geo_cross.py --model_tag T_geox8b_dis${k}_s$sd $X --seed $sd --distract $k > results/run_T_geox8b_dis${k}_s$sd.log 2>&1; done; done
  S2=$S; kill $S2
  S=$(start /SSD/huggingface/Qwen/Qwen3-14B 8086 q14b_tdis2); export POC_BASE_URL=http://127.0.0.1:8086/v1
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag T_geox14b_dis${k}_s2 $X --seed 2 --distract $k > results/run_T_geox14b_dis${k}_s2.log 2>&1; done; kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8087 q32b_tdis2); export POC_BASE_URL=http://127.0.0.1:8087/v1
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag T_geox32b_dis${k}_s2 $X --seed 2 --distract $k > results/run_T_geox32b_dis${k}_s2.log 2>&1; done; kill $S ) & L2=$!
wait $L1 $L2
echo THINKDIS2_DONE >> results/queue_log.txt
