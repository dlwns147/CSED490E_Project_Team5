#!/bin/bash
# S4d toolbox dose-response: task-matched helpers + K related (geometry) distractors, K = 0,2,4,8; control: K=8 unrelated
# (non-geometry) helpers. 8B / 14B / 32B, T=0.7, seed 1 (+ greedy for K in {0,8}).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {  # lane <model> <port> <tag> <short> [<model2> <port2> <tag2> <short2>]
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do
    for k in 0 2 4 8; do
      $P poc/run_geo_cross.py --model_tag geox${m}_dis${k}_t07s$sd --distract $k --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_dis${k}_t07s$sd.log 2>&1
    done
    $P poc/run_geo_cross.py --model_tag geox${m}_disU8_t07s$sd --distract 8 --distract_kind unrelated --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_disU8_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8062 q8b_dis 8b; lane /SSD/huggingface/Qwen/Qwen3-14B 8063 q14b_dis 14b ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8064 q32b_dis 32b & L2=$!
wait $L1 $L2
echo DISTRACT_DONE >> results/queue_distract.log
