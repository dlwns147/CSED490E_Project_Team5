#!/bin/bash
# PoC G2 on Qwen3-8B (:8000): direct no-think, code no-think (parallel), then direct think and code think
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8000/v1
$P poc/run_geo.py --model_tag geo8b_direct --mode direct --max_tokens 2048 > results/run_geo8b_direct.log 2>&1 &
L1=$!
$P poc/run_geo.py --model_tag geo8b_code --mode code --max_tokens 2048 > results/run_geo8b_code.log 2>&1 &
L2=$!
wait $L1 $L2
$P poc/run_geo.py --model_tag geo8b_direct_think --mode direct --think --max_tokens 10000 > results/run_geo8b_direct_think.log 2>&1 &
L3=$!
$P poc/run_geo.py --model_tag geo8b_code_think --mode code --think --max_tokens 10000 > results/run_geo8b_code_think.log 2>&1 &
L4=$!
wait $L3 $L4
echo GEO_DONE >> results/queue_geo.log
