#!/bin/bash
# VRPTW follow-up 3: gpt-oss drops the stated `service` header field (120b low/medium: 0-3/30 programs parse it; counterfactual re-run with a
# 4-field header makes 43/49 of its "CP Solver fail" programs optimal). Does showing the literal stdin of the instance (--show_stdin) fix it?
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
C="--arms solver --probs vrptw --n_inst 15 --repair 2 --temperature 0.7 --max_tokens 16000 --show_stdin"
run() { m=$1; eff=$2; export POC_REASONING_EFFORT=$eff
  $P poc/run_co.py --model_tag W_co${m}_nodoc_ex $C --seed 1 > results/run_W_co${m}_nodoc_ex.log 2>&1
  for sd in 1 2 3; do $P poc/run_co.py --model_tag W_co${m}_doctask_ex_s$sd $C --seed $sd --api_doc --api_doc_task > results/run_W_co${m}_doctask_ex_s$sd.log 2>&1; done; }
( S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8078 2 0.3 oss20_vrptw3) && { export POC_BASE_URL=http://127.0.0.1:8078/v1; run oss20low low; kill $S; } ) & A=$!
( while kill -0 1111762 2>/dev/null; do sleep 30; done
  S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8077 0 0.88 oss120_vrptw3) && { export POC_BASE_URL=http://127.0.0.1:8077/v1; run oss120low low; run oss120med medium; kill $S; } ) & B=$!
while kill -0 $A 2>/dev/null || kill -0 $B 2>/dev/null; do sleep 30; done
echo VRPTW3_DONE >> results/queue_log.txt
