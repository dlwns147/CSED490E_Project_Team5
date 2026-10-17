#!/bin/bash
# T1: CO metamorphic invariance, Qwen3-8B thinking off, 3 arms (+2 repairs); own server, shut down after
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8008 $2) && { echo $S; return 0; }; sleep 300; done; }
S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8008 0 0.45 q8b_t1) || exit 1   # pinned to GPU 0 (empty) after a pick race
POC_BASE_URL=http://127.0.0.1:8008/v1 $P poc/run_co_meta.py --model_tag t1_8b > results/run_t1_8b.log 2>&1
kill $S
echo T1_DONE >> results/queue_t1.log
