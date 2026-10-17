#!/bin/bash
# T1 CO-metamorphic, solver arm only, re-measured after the sandbox thread-crash fix (MALLOC_ARENA_MAX=2)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8034 q8b_t1v2)
  POC_BASE_URL=http://127.0.0.1:8034/v1 $P poc/run_co_meta.py --model_tag t1_8b_solver_v2 --arms solver > results/run_t1_8b_v2.log 2>&1
  kill $S ) & L1=$!
sleep 60
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8035 q32b_t1v2)
  POC_BASE_URL=http://127.0.0.1:8035/v1 $P poc/run_co_meta.py --model_tag t1_32b_solver_v2 --arms solver > results/run_t1_32b_v2.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo T1V2_DONE >> results/queue_t1v2.log
