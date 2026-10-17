#!/bin/bash
# VRPTW follow-up: gpt-oss-20b low misreads the 5-field header (ignores `service`, reads horizon = 10 -> "CP Solver fail" in 23/30).
# Does more reasoning effort / a larger model fix it? gpt-oss-20b medium (GPU 3), gpt-oss-120b low + medium (GPU 0): no doc / VRPTW snippet x3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
C="--arms solver --probs vrptw --n_inst 15 --repair 2 --temperature 0.7 --max_tokens 16000"
run() { m=$1; eff=$2; export POC_REASONING_EFFORT=$eff
  $P poc/run_co.py --model_tag W_co${m}_nodoc $C --seed 1 > results/run_W_co${m}_nodoc.log 2>&1
  for sd in 1 2 3; do $P poc/run_co.py --model_tag W_co${m}_doctask_s$sd $C --seed $sd --api_doc --api_doc_task > results/run_W_co${m}_doctask_s$sd.log 2>&1; done; }
( S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8076 3 0.45 oss20_vrptw2) && { export POC_BASE_URL=http://127.0.0.1:8076/v1; run oss20med medium; kill $S; } ) & A=$!
( S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8077 0 0.88 oss120_vrptw) && { export POC_BASE_URL=http://127.0.0.1:8077/v1; run oss120low low; run oss120med medium; kill $S; } ) & B=$!
wait $A $B
echo VRPTW2_DONE >> results/queue_log.txt
