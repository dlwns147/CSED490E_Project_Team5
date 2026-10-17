#!/bin/bash
# CO1 repair arm: solver + heuristic with up to 2 feedback rounds (thinking off), own 8B server on the freest GPU
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-8B 8004 q8b_co) || { echo "server failed"; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8004/v1
$P poc/run_co.py --model_tag co8b_repair2 --arms solver,heuristic --repair 2 --max_tokens 4096 > results/run_co8b_repair2.log 2>&1
kill $S
echo CO_REPAIR_DONE >> results/queue_co_repair.log
