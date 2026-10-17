#!/bin/bash
# 32B thinking Mastermind (with state summary) on GPU 1 at frac 0.75 (bigger KV cache); shut down after
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8013 1 0.75 q32b_a3b) || exit 1
POC_BASE_URL=http://127.0.0.1:8013/v1 $P poc/run_games.py --model_tag g32b_think_sp_mm --games mastermind --scratchpad --think --max_tokens 8000 > results/run_games_g32b_think_sp_mm.log 2>&1
kill $S
echo A3B_DONE >> results/queue_a3b.log
