#!/bin/bash
# PoC D follow-up: (1) 8B think rerun (ctx overflow fixed: thinking stripped from repair history, chat errors caught);
# (2) scoped CP-SAT doc arm for code (32B code failures were all CP-SAT expression misuse); (3) 32B think code re-run under the fix
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8043 q8b_zebra3); export POC_BASE_URL=http://127.0.0.1:8043/v1
  $P poc/run_zebra.py --model_tag z8b_nothink_doc --arms code --api_doc --max_tokens 4096 > results/run_zebra_z8b_nothink_doc.log 2>&1
  $P poc/run_zebra.py --model_tag z8b_think --think --max_tokens 20000 > results/run_zebra_z8b_think.log 2>&1
  $P poc/run_zebra.py --model_tag z8b_think_doc --arms code --api_doc --think --max_tokens 20000 > results/run_zebra_z8b_think_doc.log 2>&1
  kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8044 q32b_zebra3); export POC_BASE_URL=http://127.0.0.1:8044/v1
  $P poc/run_zebra.py --model_tag z32b_nothink_doc --arms code --api_doc --max_tokens 4096 > results/run_zebra_z32b_nothink_doc.log 2>&1
  $P poc/run_zebra.py --model_tag z32b_think_doc --arms code --api_doc --think --max_tokens 20000 > results/run_zebra_z32b_think_doc.log 2>&1
  $P poc/run_zebra.py --model_tag z32b_think_code2 --arms code --think --max_tokens 20000 > results/run_zebra_z32b_think_code2.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo ZEBRA3_DONE >> results/queue_zebra.log
