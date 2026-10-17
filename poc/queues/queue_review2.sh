#!/bin/bash
# Review item 2: neutral toolbox header ("The following tested helper functions are available:", no instruction), K=0 vs K=8, n=300, --stdlib, T=0.7 s1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start /SSD/huggingface/Qwen/$1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag F_geox${m}_dis${k}neu_t07s1 --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1 --distract $k --tb_head neutral > results/run_F_geox${m}_dis${k}neu.log 2>&1; done
  kill $S; }
lane Qwen3-8B 8063 q8b_neu 8b & L1=$!
sleep 30
lane Qwen3-14B 8064 q14b_neu 14b & L2=$!
sleep 30
lane Qwen3-32B-AWQ 8065 q32b_neu 32b & L3=$!
wait $L1 $L2 $L3
echo REVIEW2_DONE >> results/queue_log.txt
