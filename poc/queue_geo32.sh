#!/bin/bash
# G2 scale point: Qwen3-32B-AWQ, direct + code (thinking off) and cross-variant code; own server, shut down after
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8005 $2) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b_geo)
export POC_BASE_URL=http://127.0.0.1:8005/v1
$P poc/run_geo.py --model_tag geo32b_direct --mode direct --max_tokens 4096 > results/run_geo32b_direct.log 2>&1 &
L1=$!
$P poc/run_geo.py --model_tag geo32b_code --mode code --max_tokens 4096 > results/run_geo32b_code.log 2>&1 &
L2=$!
$P poc/run_geo_cross.py --model_tag geox32b --max_tokens 4096 > results/run_geox32b.log 2>&1 &
L3=$!
wait $L1 $L2 $L3
kill $S
echo GEO32_DONE >> results/queue_geo32.log
