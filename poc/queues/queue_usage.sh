#!/bin/bash
# (a) 14B interface misuse: toolbox K=0/K=8 with an explicit API contract line (points are tuples + example calls); n=300, --stdlib, T=0.7 s1.
# (b) held-out CO third seed (best-of-3) for doc and doctask, 8B/14B/32B.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
co3() { m=$1; X="--probs binpack,vcover --n_inst 18 --temperature 0.7 --seed 3 --repair 2 --arms solver"
  $P poc/run_co.py --model_tag H_co${m}_doc_s3 --api_doc $X > results/run_H_co${m}_doc_s3.log 2>&1
  $P poc/run_co.py --model_tag H_co${m}_doctask_s3 --api_doc_task $X > results/run_H_co${m}_doctask_s3.log 2>&1; }
( S=$(start /SSD/huggingface/Qwen/Qwen3-14B 8065 q14b_usage); export POC_BASE_URL=http://127.0.0.1:8065/v1
  G="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1 --tb_usage"
  $P poc/run_geo_cross.py --model_tag F_geox14b_dis0use_t07s1 $G --distract 0 > results/run_F_geox14b_dis0use_t07s1.log 2>&1
  $P poc/run_geo_cross.py --model_tag F_geox14b_dis8use_t07s1 $G --distract 8 > results/run_F_geox14b_dis8use_t07s1.log 2>&1
  co3 14b; kill $S ) & L1=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8066 q8b_usage); export POC_BASE_URL=http://127.0.0.1:8066/v1; co3 8b; kill $S ) & L2=$!
sleep 30
( S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8067 q32b_usage); export POC_BASE_URL=http://127.0.0.1:8067/v1; co3 32b; kill $S ) & L3=$!
wait $L1 $L2 $L3
echo USAGE_DONE >> results/queue_distract.log
