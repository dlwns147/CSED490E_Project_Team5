#!/bin/bash
# Re-measure the Qwen geometry baseline with the stdlib environment fact (audit: 3-20/100 baseline programs import shapely/numpy and crash,
# 14B and 72B worst). Arms: base vs task-matched, both --stdlib; greedy + T=0.7 seeds 1-3. 8B / 14B / 32B. Ports 8100+.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  $P poc/run_geo_cross.py --model_tag geox${m}_std --stdlib --max_tokens 4096 > results/run_geox${m}_std.log 2>&1
  $P poc/run_geo_cross.py --model_tag geox${m}_std_prims_task --stdlib --primitives --prims_task --max_tokens 4096 > results/run_geox${m}_std_prims_task.log 2>&1
  for sd in 1 2 3; do
    $P poc/run_geo_cross.py --model_tag geox${m}_stdbase_t07s$sd --stdlib --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_stdbase_t07s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag geox${m}_stdpt_t07s$sd --stdlib --primitives --prims_task --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_stdpt_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8104 q8b_std 8b; lane /SSD/huggingface/Qwen/Qwen3-14B 8105 q14b_std 14b ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8106 q32b_std 32b & L2=$!
wait $L1 $L2
echo QSTD_DONE >> results/queue_distract.log
