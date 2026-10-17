#!/bin/bash
# Review item 3, optimization side: realistic CVRP (capacitated vehicle routing; 8/12/16 customers x 10 inst = 30; exact CP-SAT references).
# Qwen3 8B (GPU 0) / 32B-AWQ (GPU 1), then 14B (GPU 0): solver arm, repair 2, T=0.7: no doc / full cheat sheet (has TSP routing, NOT the
# capacity dimension) / CVRP snippet x 3 seeds (best-of-3) / snippet + thinking / snippet + budget 2048.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { S=$(poc/start_server.sh /SSD/huggingface/Qwen/$1 $2 $3 0.45 $4) || { echo "$4 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$5; X="--arms solver --probs cvrp --n_inst 10 --repair 2 --temperature 0.7"
  $P poc/run_co.py --model_tag V_co${m}_nodoc_s1 $X --seed 1 > results/run_V_co${m}_nodoc.log 2>&1
  $P poc/run_co.py --model_tag V_co${m}_doc_s1 $X --seed 1 --api_doc > results/run_V_co${m}_doc.log 2>&1
  for sd in 1 2 3; do $P poc/run_co.py --model_tag V_co${m}_doctask_s$sd $X --seed $sd --api_doc --api_doc_task > results/run_V_co${m}_doctask_s$sd.log 2>&1; done
  $P poc/run_co.py --model_tag V_co${m}_doctask_b2048 $X --seed 1 --api_doc --api_doc_task --think_budget 2048 > results/run_V_co${m}_b2048.log 2>&1
  $P poc/run_co.py --model_tag V_co${m}_doctask_think $X --seed 1 --api_doc --api_doc_task --think --max_tokens 20000 > results/run_V_co${m}_think.log 2>&1
  $P poc/run_co.py --model_tag V_co${m}_nodoc_think $X --seed 1 --think --max_tokens 20000 > results/run_V_co${m}_nodoc_think.log 2>&1
  kill $S; }
( lane Qwen3-8B 8087 0 q8b_cvrp 8b; lane Qwen3-14B 8089 0 q14b_cvrp 14b ) & L1=$!
sleep 30
lane Qwen3-32B-AWQ 8088 1 q32b_cvrp 32b & L2=$!
wait $L1 $L2
echo CVRP_DONE >> results/queue_log.txt
