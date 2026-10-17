#!/bin/bash
# T3: robustness hint for LLM geometry code (cross-variant execution), 8B and 32B, thinking off
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8007 $2) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B q8b_t3)
POC_BASE_URL=http://127.0.0.1:8007/v1 $P poc/run_geo_cross.py --model_tag geox8b_robust --robust_hint > results/run_geox8b_robust.log 2>&1
kill $S; sleep 20
S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b_t3)
POC_BASE_URL=http://127.0.0.1:8007/v1 $P poc/run_geo_cross.py --model_tag geox32b_robust --robust_hint --max_tokens 4096 > results/run_geox32b_robust.log 2>&1
kill $S
echo T3_DONE >> results/queue_t3.log
