#!/bin/bash
# Parallelise the budget sweep: 14B and 32B lanes now (GPUs free); queue_budget.sh keeps only its 8B lane (a watcher stops it after 8B b4096).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start /SSD/huggingface/Qwen/$1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for B in 0 256 1024 4096; do $P poc/run_geo_cross.py --model_tag B_geox${m}_dis8_b$B --stdlib --distract 8 --think_budget $B --max_tokens 4096 --temperature 0.7 --seed 1 > results/run_B_geox${m}_dis8_b$B.log 2>&1; done
  kill $S; }
lane Qwen3-14B 8090 q14b_budget2 14b & L1=$!
sleep 30
lane Qwen3-32B-AWQ 8091 q32b_budget2 32b & L2=$!
wait $L1 $L2
echo BUDGET2_DONE >> results/queue_log.txt
