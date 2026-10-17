#!/bin/bash
# S-A3: the no-repeat check was gamed (programs switched to lexicographic enumeration AAAA, AAAB, ...). Stronger behavioural
# check: a guess that past feedback rules out triggers a repair with a counter-example.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-8B 8048 q8b_conscheck 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8048/v1
$P poc/run_games.py --model_tag mm8b_code_think20k_cons --games mastermind --code --think --code_repair 2 --no_repeat --consistent_check --max_tokens 20000 > results/run_games_mm8b_code_think20k_cons.log 2>&1
$P poc/run_games.py --model_tag mm8b_code_rep2_cons --games mastermind --code --code_repair 2 --no_repeat --consistent_check --max_tokens 4096 > results/run_games_mm8b_code_rep2_cons.log 2>&1
kill $S
echo CONS_DONE >> results/queue_mmsol.log
