#!/bin/bash
# S5b/S5c better self-scoping: pointwise yes/no per helper; plan-first (plan without helpers, then select against the plan). K=8 pool,
# 8B / 14B / 32B, T=0.7, 2 seeds. Compare auto8 (pick list) 80/83.5/85, dis8 74.5/75/75.5, oracle 98/84.5/95.5.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do for mode in pointwise plan; do
    $P poc/run_geo_cross.py --model_tag geox${m}_auto8${mode}_t07s$sd --distract 8 --autoscope --autoscope_mode $mode --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_auto8${mode}_t07s$sd.log 2>&1
  done; done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8073 q8b_auto2 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8074 q14b_auto2 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8075 q32b_auto2 32b & L3=$!
wait $L1 $L2 $L3
echo AUTO2_DONE >> results/queue_distract.log
