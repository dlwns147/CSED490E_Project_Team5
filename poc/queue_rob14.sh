#!/bin/bash
# Robustness at the sweet-spot size (14B) under sampling (T=0.7, seeds 1-2): zebra code+snippet+status (no think, all cells),
# zebra direct+think vs code+snippet+status+think (5x5/6x5), geometry base vs task-matched predicates.
# Lane 2: does the status line also rescue 8B zebra code (no think / think)?
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-14B 8054 q14b_rob); export POC_BASE_URL=http://127.0.0.1:8054/v1
  for sd in 1 2; do
    $P poc/run_zebra.py --model_tag z14b_nothink_docst_t07s$sd --arms code --api_doc --doc_status --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_zebra_z14b_nothink_docst_t07s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag geox14b_base_t07s$sd --temperature 0.7 --seed $sd --max_tokens 2048 > results/run_geox14b_base_t07s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag geox14b_prims_task_t07s$sd --primitives --prims_task --temperature 0.7 --seed $sd --max_tokens 2048 > results/run_geox14b_prims_task_t07s$sd.log 2>&1
    $P poc/run_zebra.py --model_tag z14b_think_direct_t07s$sd --arms direct --think --cells 5x5,6x5 --temperature 0.7 --seed $sd --max_tokens 20000 > results/run_zebra_z14b_think_direct_t07s$sd.log 2>&1
    $P poc/run_zebra.py --model_tag z14b_think_docst_t07s$sd --arms code --api_doc --doc_status --think --cells 5x5,6x5 --temperature 0.7 --seed $sd --max_tokens 20000 > results/run_zebra_z14b_think_docst_t07s$sd.log 2>&1
  done
  kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8055 q8b_zst); export POC_BASE_URL=http://127.0.0.1:8055/v1
  $P poc/run_zebra.py --model_tag z8b_nothink_docst --arms code --api_doc --doc_status --max_tokens 4096 > results/run_zebra_z8b_nothink_docst.log 2>&1
  $P poc/run_zebra.py --model_tag z8b_think_docst --arms code --api_doc --doc_status --think --max_tokens 20000 > results/run_zebra_z8b_think_docst.log 2>&1
  kill $S ) & L2=$!
wait $L1 $L2
echo ROB14_DONE >> results/queue_zebra.log
