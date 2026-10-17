#!/bin/bash
# T2: build a pool of subtly-wrong geometry programs (8B, then 32B), then run the 4 hack strategies with the 8B
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8009 $2 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b_t2)
POC_BASE_URL=http://127.0.0.1:8009/v1 $P poc/run_geo_pool.py --model_tag p32b > results/run_geopool_p32b.log 2>&1
kill $S; sleep 20
S=$(start /SSD/huggingface/Qwen/Qwen3-8B q8b_t2)
export POC_BASE_URL=http://127.0.0.1:8009/v1
$P poc/run_geo_pool.py --model_tag p8b > results/run_geopool_p8b.log 2>&1
echo POOL_DONE >> results/queue_t2.log
kill $S
echo T2_POOL_DONE >> results/queue_t2.log
