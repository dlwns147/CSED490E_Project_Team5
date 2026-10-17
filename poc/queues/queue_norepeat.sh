#!/bin/bash
# S-A3 follow-up: 8B code-policy + think failures were all constant-guess loops (AAAA x10) that never triggered repair.
# --no_repeat makes a repeated guess trigger a program repair. 8B (main test) and 32B (ceiling check not needed: 30/30).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-8B 8047 q8b_norepeat 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8047/v1
$P poc/run_games.py --model_tag mm8b_code_think20k_norep --games mastermind --code --think --code_repair 2 --no_repeat --max_tokens 20000 > results/run_games_mm8b_code_think20k_norep.log 2>&1
$P poc/run_games.py --model_tag mm8b_code_rep2_norep --games mastermind --code --code_repair 2 --no_repeat --max_tokens 4096 > results/run_games_mm8b_code_rep2_norep.log 2>&1
kill $S
echo NOREP_DONE >> results/queue_mmsol.log
