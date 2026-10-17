#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8009 $2 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B q8b_t2b)
POC_BASE_URL=http://127.0.0.1:8009/v1 $P poc/run_geo_hack.py --model_tag t2_8b --pools p32b,p8b > results/run_geohack_t2_8b.log 2>&1
kill $S
echo T2B_DONE >> results/queue_t2b.log
