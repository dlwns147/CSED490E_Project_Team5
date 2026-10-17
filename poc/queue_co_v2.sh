#!/bin/bash
# CO solver arms re-run after the sandbox fix (MALLOC_ARENA_MAX=2): CP-SAT threads had randomly crashed ('Resource
# temporarily unavailable' / 'thread-local data') under RLIMIT_AS, contaminating all earlier solver-arm numbers.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
arms() {  # arms <url> <size>
  for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task" "doctask_shim:--api_doc_task --shim" "shim:--shim"; do
    n=${v%%:*}; x=${v#*:}
    POC_BASE_URL=$1 $P poc/run_co.py --model_tag co$2_${n}_r2_v2 --arms solver $x --repair 2 > results/run_co$2_${n}_v2.log 2>&1
  done
}
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8032 q8b_cov2); arms http://127.0.0.1:8032/v1 8b; kill $S ) & L1=$!
sleep 60
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8033 q32b_cov2); arms http://127.0.0.1:8033/v1 32b; kill $S ) & L2=$!
wait $L1 $L2
echo COV2_DONE >> results/queue_co_v2.log
