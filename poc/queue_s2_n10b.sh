#!/bin/bash
# N10 stage 2 (PREREG_N10.md P4): LLM router, Qwen3-32B-AWQ on 8041 (GPU 1).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8041 1 0.88 n10b) || exit 1
POC_BASE_URL=http://127.0.0.1:8041/v1 $P poc/n10_llm_router.py > results/n10_llm_router.log 2>&1
kill $S
echo "S2_N10b (LLM router) done $(date)" >> results/queue_log.txt
