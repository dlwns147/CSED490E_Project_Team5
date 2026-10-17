#!/bin/bash
# PoC D: NL->solver (code) vs direct on zebra puzzles 3x3..6x5, thinking off/on, 8B and 32B lanes
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {  # lane <model> <port> <tag> <short>
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1
  $P poc/run_zebra.py --model_tag z$4_nothink --max_tokens 4096 > results/run_zebra_z$4_nothink.log 2>&1
  $P poc/run_zebra.py --model_tag z$4_think --think --max_tokens 20000 > results/run_zebra_z$4_think.log 2>&1
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8041 q8b_zebra 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8042 q32b_zebra 32b & L2=$!
wait $L1 $L2
echo ZEBRA_DONE >> results/queue_zebra.log
