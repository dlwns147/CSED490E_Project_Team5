#!/bin/bash
# CO1 follow-ups, waiting (no time limit) for a GPU with room: (1) 8B solver arm + OR-Tools API doc, +repair;
# (2) Qwen3-32B-AWQ solver/heuristic with repair (scale). Server shut down after each.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 8004 $2) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B q8b_co)
POC_BASE_URL=http://127.0.0.1:8004/v1 $P poc/run_co.py --model_tag co8b_doc_repair2 --arms solver --api_doc --repair 2 > results/run_co8b_doc.log 2>&1
kill $S; sleep 20
S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b_co)
POC_BASE_URL=http://127.0.0.1:8004/v1 $P poc/run_co.py --model_tag co32b_repair2 --arms direct,solver,heuristic --repair 2 > results/run_co32b.log 2>&1
kill $S
echo CO2_DONE >> results/queue_co2.log
