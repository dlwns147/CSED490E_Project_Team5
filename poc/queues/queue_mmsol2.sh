#!/bin/bash
# S-A3 follow-ups: code policy + program repair; code policy with thinking at a 20k budget (8k truncated: 29/30 no code)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
G="--games mastermind --code"
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8039 q8b_mmsol2); export POC_BASE_URL=http://127.0.0.1:8039/v1
  $P poc/run_games.py --model_tag mm8b_code_rep2 $G --code_repair 2 --max_tokens 4096 > results/run_games_mm8b_code_rep2.log 2>&1
  $P poc/run_games.py --model_tag mm8b_code_think20k $G --think --code_repair 2 --max_tokens 20000 > results/run_games_mm8b_code_think20k.log 2>&1
  kill $S ) & L1=$!
sleep 60
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8040 q32b_mmsol2); export POC_BASE_URL=http://127.0.0.1:8040/v1
  $P poc/run_games.py --model_tag mm32b_code_rep2 $G --code_repair 2 --max_tokens 4096 > results/run_games_mm32b_code_rep2.log 2>&1
  $P poc/run_games.py --model_tag mm32b_code_think20k $G --think --code_repair 2 --max_tokens 20000 > results/run_games_mm32b_code_think20k.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo MMSOL2_DONE >> results/queue_mmsol.log
