#!/bin/bash
# second Qwen3-8B server on GPU 2 (:8003) for the cross-variant G2 runs; shut down when done
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8003 2 0.45 q8b_b) || { echo "8B-b failed"; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8003/v1
$P poc/run_geo_cross.py --model_tag geox8b > results/run_geox8b.log 2>&1
$P poc/run_geo_cross.py --model_tag geox8b_think --think --max_tokens 10000 > results/run_geox8b_think.log 2>&1
kill $S
echo GEOX_DONE >> results/queue_geo_cross2.log
