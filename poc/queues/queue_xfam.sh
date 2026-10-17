#!/bin/bash
# (1) Do the fixes transfer to another family? Llama-3.1-8B: zebra direct/code/code+snippet; geometry base vs task-matched
#     predicates. (2) Is the 32B zebra headline robust? 5x5/6x5 at T=0.7, 2 seeds: direct+think vs code+snippet+think.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
( S=$(start /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8045 llama8b_xfam); export POC_BASE_URL=http://127.0.0.1:8045/v1
  $P poc/run_zebra.py --model_tag zllama8b --max_tokens 4096 > results/run_zebra_zllama8b.log 2>&1
  $P poc/run_zebra.py --model_tag zllama8b_doc --arms code --api_doc --max_tokens 4096 > results/run_zebra_zllama8b_doc.log 2>&1
  $P poc/run_geo_cross.py --model_tag geoxllama8b_prims_task --primitives --prims_task --max_tokens 2048 > results/run_geoxllama8b_prims_task.log 2>&1
  $P poc/run_geo_cross.py --model_tag geoxllama8b_prims --primitives --max_tokens 2048 > results/run_geoxllama8b_prims.log 2>&1
  kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8046 q32b_zrep); export POC_BASE_URL=http://127.0.0.1:8046/v1
  for sd in 1 2; do
    $P poc/run_zebra.py --model_tag z32b_think_direct_t07s$sd --arms direct --think --cells 5x5,6x5 --temperature 0.7 --seed $sd --max_tokens 20000 > results/run_zebra_z32b_think_direct_t07s$sd.log 2>&1
    $P poc/run_zebra.py --model_tag z32b_think_doc_t07s$sd --arms code --api_doc --think --cells 5x5,6x5 --temperature 0.7 --seed $sd --max_tokens 20000 > results/run_zebra_z32b_think_doc_t07s$sd.log 2>&1
  done
  kill $S ) & L2=$!
wait $L1 $L2
echo XFAM_DONE >> results/queue_xfam.log
