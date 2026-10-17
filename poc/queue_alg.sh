#!/bin/bash
# non-coding algorithmic topics: A (interactive games) on 8B no-think + think; F (hints) tutor 8B -> student 1.7B
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8000/v1
$P poc/run_games.py --model_tag g8b_nothink --max_tokens 1024 > results/run_games_g8b_nothink.log 2>&1 &
G1=$!
until curl -sf localhost:8001/health >/dev/null; do sleep 10; done
$P poc/run_hints.py --tag t8b_s17b > results/run_hints_t8b_s17b.log 2>&1 &
H1=$!
wait $G1
$P poc/run_games.py --model_tag g8b_think --think --max_tokens 6000 > results/run_games_g8b_think.log 2>&1
wait $H1
echo ALG_DONE >> results/queue_alg.log
