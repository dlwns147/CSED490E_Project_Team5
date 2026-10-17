#!/bin/bash
# Topic A state-tracking control: games with an environment-provided state summary, 8B thinking off and on
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8012 $2 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B q8b_a2)
export POC_BASE_URL=http://127.0.0.1:8012/v1
$P poc/run_games.py --model_tag g8b_nothink_sp --scratchpad --max_tokens 1024 > results/run_games_g8b_nothink_sp.log 2>&1
$P poc/run_games.py --model_tag g8b_think_sp --scratchpad --think --max_tokens 6000 > results/run_games_g8b_think_sp.log 2>&1
kill $S
echo A2_DONE >> results/queue_a2.log
