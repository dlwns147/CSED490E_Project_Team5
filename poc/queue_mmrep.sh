#!/bin/bash
# Mastermind headline replicates (same 30 secrets, new sampling seeds): 8B code+think+consistency check, 32B code+repair, 32B code+think
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8060 q8b_mmrep); export POC_BASE_URL=http://127.0.0.1:8060/v1
  for r in 1 2; do $P poc/run_games.py --model_tag mm8b_code_think20k_cons_rep$r --seed_rep $r --games mastermind --code --think --code_repair 2 --no_repeat --consistent_check --max_tokens 20000 > results/run_games_mm8b_code_think20k_cons_rep$r.log 2>&1; done
  kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8061 q32b_mmrep); export POC_BASE_URL=http://127.0.0.1:8061/v1
  for r in 1 2; do
    $P poc/run_games.py --model_tag mm32b_code_rep2_rep$r --seed_rep $r --games mastermind --code --code_repair 2 --max_tokens 4096 > results/run_games_mm32b_code_rep2_rep$r.log 2>&1
    $P poc/run_games.py --model_tag mm32b_code_think20k_rep$r --seed_rep $r --games mastermind --code --think --code_repair 2 --max_tokens 20000 > results/run_games_mm32b_code_think20k_rep$r.log 2>&1
  done
  kill $S ) & L2=$!
wait $L1 $L2
echo MMREP_DONE >> results/queue_mmsol.log
