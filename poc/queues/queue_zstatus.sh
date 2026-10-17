#!/bin/bash
# zebra code+snippet, no think, with the status-check line (14B printed "No solution found" on solved 3x3 models: st != FEASIBLE)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-14B 8052 q14b_zstatus); export POC_BASE_URL=http://127.0.0.1:8052/v1
  $P poc/run_zebra.py --model_tag z14b_nothink_docst --arms code --api_doc --doc_status --max_tokens 4096 > results/run_zebra_z14b_nothink_docst.log 2>&1
  kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8053 q32b_zstatus); export POC_BASE_URL=http://127.0.0.1:8053/v1
  $P poc/run_zebra.py --model_tag z32b_nothink_docst --arms code --api_doc --doc_status --max_tokens 4096 > results/run_zebra_z32b_nothink_docst.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo ZSTATUS_DONE >> results/queue_zebra.log
