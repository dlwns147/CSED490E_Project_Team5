#!/bin/bash
# G2 canonicalize-then-solve (direct, 8B) + CO1 best-of-4 direct (8B), own 8B server on the freest GPU; shut down after
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8006 $2) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B q8b_next)
export POC_BASE_URL=http://127.0.0.1:8006/v1
$P poc/run_geo.py --model_tag geo8b_direct_canon --mode direct --canon --max_tokens 4096 > results/run_geo8b_canon.log 2>&1 &
L1=$!
$P poc/run_co.py --model_tag co8b_bo4 --arms direct_bo4 --max_tokens 4096 > results/run_co8b_bo4.log 2>&1 &
L2=$!
wait $L1 $L2
kill $S
echo NEXT_CGCO_DONE >> results/queue_next_cgco.log
