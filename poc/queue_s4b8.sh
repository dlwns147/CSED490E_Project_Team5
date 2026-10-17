#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8024 q8b_s4b)
export POC_BASE_URL=http://127.0.0.1:8024/v1
$P poc/run_geo_cross.py --model_tag geox8b_prims_task --primitives --prims_task --max_tokens 2048 > results/run_geox8b_prims_task.log 2>&1
kill $S
echo S4B8_DONE >> results/queue_s4b.log
