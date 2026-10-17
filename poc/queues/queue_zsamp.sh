#!/bin/bash
# S6 for zebra: k=5 sampled code programs WITHOUT the snippet (no think); offline selection by label-free clue verification
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2 3 4 5; do
    $P poc/run_zebra.py --model_tag z${m}_code_t07s$sd --arms code --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_zebra_z${m}_code_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8080 q8b_zsamp 8b; lane /SSD/huggingface/Qwen/Qwen3-14B 8081 q14b_zsamp 14b ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8082 q32b_zsamp 32b & L2=$!
wait $L1 $L2
echo ZSAMP_DONE >> results/queue_zebra.log
