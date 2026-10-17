#!/bin/bash
# PoC A solutions for Mastermind deduction: S-A1 verifier (reject inconsistent guesses with a counter-example),
# S-A3 code-as-policy (model writes the codebreaker program; env runs it each turn).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
G="--games mastermind"
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8037 q8b_mmsol); export POC_BASE_URL=http://127.0.0.1:8037/v1
  $P poc/run_games.py --model_tag mm8b_code $G --code --max_tokens 4096 > results/run_games_mm8b_code.log 2>&1
  $P poc/run_games.py --model_tag mm8b_code_think $G --code --think --max_tokens 8192 > results/run_games_mm8b_code_think.log 2>&1
  $P poc/run_games.py --model_tag mm8b_sp_verify3 $G --scratchpad --verify 3 > results/run_games_mm8b_sp_verify3.log 2>&1
  $P poc/run_games.py --model_tag mm8b_think_sp_verify3 $G --think --scratchpad --verify 3 --max_tokens 6144 > results/run_games_mm8b_think_sp_verify3.log 2>&1
  kill $S ) & L1=$!
sleep 60
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8038 q32b_mmsol); export POC_BASE_URL=http://127.0.0.1:8038/v1
  $P poc/run_games.py --model_tag mm32b_code $G --code --max_tokens 4096 > results/run_games_mm32b_code.log 2>&1
  $P poc/run_games.py --model_tag mm32b_code_think $G --code --think --max_tokens 8192 > results/run_games_mm32b_code_think.log 2>&1
  $P poc/run_games.py --model_tag mm32b_sp_verify3 $G --scratchpad --verify 3 > results/run_games_mm32b_sp_verify3.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo MMSOL_DONE >> results/queue_mmsol.log
