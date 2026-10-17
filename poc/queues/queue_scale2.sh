#!/bin/bash
# parallel lanes on separate GPUs: (1) T1 CO metamorphic at Qwen3-32B; (2) G2 direct/code/cross with Llama-3.1-8B
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
(
  S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8010 q32b_t1)
  POC_BASE_URL=http://127.0.0.1:8010/v1 $P poc/run_co_meta.py --model_tag t1_32b > results/run_t1_32b.log 2>&1
  kill $S
) &
L1=$!
sleep 240   # let the first server load so the next pick sees its memory
(
  S=$(start /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8011 llama8b_geo)
  export POC_BASE_URL=http://127.0.0.1:8011/v1
  $P poc/run_geo.py --model_tag geollama8b_direct --mode direct --max_tokens 2048 > results/run_geollama_direct.log 2>&1 &
  A=$!
  $P poc/run_geo.py --model_tag geollama8b_code --mode code --max_tokens 2048 > results/run_geollama_code.log 2>&1 &
  B=$!
  $P poc/run_geo_cross.py --model_tag geoxllama8b > results/run_geoxllama8b.log 2>&1 &
  C=$!
  wait $A $B $C
  kill $S
) &
L2=$!
wait $L1 $L2
echo SCALE2_DONE >> results/queue_scale2.log
