#!/bin/bash
# S5 auto-scope: the model chooses its helpers from the K=8 pool (catalog of one-line docs), then gets only those.
# Compare: dis8 (all 8 given), dis0 (oracle task-matched). 8B / 14B / 32B, T=0.7, 2 seeds.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do
    $P poc/run_geo_cross.py --model_tag geox${m}_auto8_t07s$sd --distract 8 --autoscope --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_auto8_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8070 q8b_auto 8b; lane /SSD/huggingface/Qwen/Qwen3-14B 8071 q14b_auto 14b ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8072 q32b_auto 32b & L2=$!
wait $L1 $L2
echo AUTO_DONE >> results/queue_distract.log
