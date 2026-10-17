#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
export POC_BASE_URL=http://127.0.0.1:8000/v1
P=/root/venvs/llm_algo_poc/bin/python
$P poc/run_games.py --model_tag g8b_nothink --max_tokens 1024 > results/run_games_g8b_nothink.log 2>&1
$P poc/run_games.py --model_tag g8b_think --think --max_tokens 6000 > results/run_games_g8b_think.log 2>&1
echo GAMES_DONE >> results/run_games_g8b_think.log
