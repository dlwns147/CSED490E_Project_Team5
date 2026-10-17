#!/bin/bash
# Capability via reasoning: does thinking make Qwen3 robust to plausible helpers? K=0 vs K=8, --think (20k), n=100 (n_inst 10), --stdlib, T=0.7 s1; 14B and 32B.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--stdlib --think --max_tokens 20000 --temperature 0.7 --seed 1"
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag T_geox${m}_dis${k} $X --distract $k > results/run_T_geox${m}_dis${k}.log 2>&1; done; kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-14B 8083 q14b_tdis 14b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8084 q32b_tdis 32b & L2=$!
wait $L1 $L2
echo THINKDIS_DONE >> results/queue_log.txt
