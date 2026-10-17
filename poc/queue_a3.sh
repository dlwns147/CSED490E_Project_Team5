#!/bin/bash
# Topic A at 32B: games with state summary (thinking off and on) — does scale fix Mastermind deduction?
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8013 $2 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b_a3)
export POC_BASE_URL=http://127.0.0.1:8013/v1
$P poc/run_games.py --model_tag g32b_nothink_sp --scratchpad --max_tokens 1024 > results/run_games_g32b_nothink_sp.log 2>&1
$P poc/run_games.py --model_tag g32b_think_sp --scratchpad --think --max_tokens 8000 > results/run_games_g32b_think_sp.log 2>&1
kill $S
echo A3_DONE >> results/queue_a3.log
