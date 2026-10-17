#!/bin/bash
# CO analogue of geometry S4b: full OR-Tools cheat sheet vs problem-scoped API snippet (solver arm, repair 2), 8B + 32B
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8027 q8b_codoc)
  POC_BASE_URL=http://127.0.0.1:8027/v1 $P poc/run_co.py --model_tag co8b_doctask_repair2 --arms solver --api_doc_task --repair 2 > results/run_co8b_doctask.log 2>&1
  kill $S ) & L1=$!
sleep 60
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8028 q32b_codoc)
  POC_BASE_URL=http://127.0.0.1:8028/v1 $P poc/run_co.py --model_tag co32b_doctask_repair2 --arms solver --api_doc_task --repair 2 > results/run_co32b_doctask.log 2>&1
  POC_BASE_URL=http://127.0.0.1:8028/v1 $P poc/run_co.py --model_tag co32b_doc_repair2 --arms solver --api_doc --repair 2 > results/run_co32b_doc.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo CODOC_DONE >> results/queue_codoc.log
