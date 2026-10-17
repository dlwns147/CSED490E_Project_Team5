#!/bin/bash
# Review item 3 (optimization side, "time windows"): VRPTW (capacities + time windows; 8/12 customers x 15 = 30 inst; exact CP-SAT refs;
# correct-program ceiling 20/20). Arms (solver, repair 2, T=0.7): no doc / full sheet / NEAR-MISS CVRP snippet (no time dimension) /
# VRPTW snippet s1-3 (best-of-3) / snippet + thinking (Qwen). Qwen3-8B (GPU 0) + 32B (GPU 1), Llama-70B (GPU 3), then gpt-oss-20b low (GPU 0).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { S=$(poc/start_server.sh $1 $2 $3 $4 $5) || { echo "$5 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$6; [ -n "$7" ] && export POC_REASONING_EFFORT=$7 || unset POC_REASONING_EFFORT
  C="--arms solver --probs vrptw --n_inst 15 --repair 2 --temperature 0.7 --max_tokens 16000"
  $P poc/run_co.py --model_tag W_co${m}_nodoc $C --seed 1 > results/run_W_co${m}_nodoc.log 2>&1
  $P poc/run_co.py --model_tag W_co${m}_doc $C --seed 1 --api_doc > results/run_W_co${m}_doc.log 2>&1
  $P poc/run_co.py --model_tag W_co${m}_cvrpdoc $C --seed 1 --api_doc --api_doc_task --api_doc_as cvrp > results/run_W_co${m}_cvrpdoc.log 2>&1
  for sd in 1 2 3; do $P poc/run_co.py --model_tag W_co${m}_doctask_s$sd $C --seed $sd --api_doc --api_doc_task > results/run_W_co${m}_doctask_s$sd.log 2>&1; done
  if [ "${m:0:1}" = "q" ]; then $P poc/run_co.py --model_tag W_co${m}_doctask_think $C --seed 1 --api_doc --api_doc_task --think --max_tokens 20000 > results/run_W_co${m}_think.log 2>&1; fi
  kill $S; sleep 15; }
( lane /SSD/huggingface/Qwen/Qwen3-8B 8073 0 0.45 q8b_vrptw q8b; lane /SSD/huggingface/openai/gpt-oss-20b 8073 0 0.45 oss20_vrptw oss20low low ) & A=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8074 1 0.45 q32b_vrptw q32b & B=$!
sleep 30
lane /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8075 3 0.7 llama70_vrptw l70 & C=$!
wait $A $B $C
echo VRPTW_DONE >> results/queue_log.txt
