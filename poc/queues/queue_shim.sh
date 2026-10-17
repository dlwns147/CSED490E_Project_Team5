#!/bin/bash
# CO solver arm under the OR-Tools misconception shim (poc/api_shim.py): does tolerating known misuse fix 8B TSP/sched?
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8030 q8b_shim)
  U=http://127.0.0.1:8030/v1
  POC_BASE_URL=$U $P poc/run_co.py --model_tag co8b_doctask_shim_repair2 --arms solver --api_doc_task --shim --repair 2 > results/run_co8b_doctask_shim.log 2>&1
  POC_BASE_URL=$U $P poc/run_co.py --model_tag co8b_shim_repair2 --arms solver --shim --repair 2 > results/run_co8b_shim.log 2>&1
  kill $S ) & L1=$!
sleep 60
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8031 q32b_shim)
  POC_BASE_URL=http://127.0.0.1:8031/v1 $P poc/run_co.py --model_tag co32b_doctask_shim_repair2 --arms solver --api_doc_task --shim --repair 2 > results/run_co32b_doctask_shim.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo SHIM_DONE >> results/queue_shim.log
