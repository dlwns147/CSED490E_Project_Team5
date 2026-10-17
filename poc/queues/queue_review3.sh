#!/bin/bash
# Review item 3: 5x larger instances (hull/close 50-100 points, polygons 40-70 vertices, 30-50 segments), --stdlib, n_inst 20 (200 programs):
# greedy base / task-matched; T=0.7 base x3 (MR-select); K=0 / K=8 toolbox (s1). Qwen3 8B/14B/32B.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start /SSD/huggingface/Qwen/$1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--stdlib --size_mult 5 --n_inst 20 --max_tokens 4096"
  $P poc/run_geo_cross.py --model_tag L_geox${m}_base $X > results/run_L_geox${m}_base.log 2>&1
  $P poc/run_geo_cross.py --model_tag L_geox${m}_pt $X --primitives --prims_task > results/run_L_geox${m}_pt.log 2>&1
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag L_geox${m}_base_t07s$sd $X --temperature 0.7 --seed $sd > results/run_L_geox${m}_base_t07s$sd.log 2>&1; done
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag L_geox${m}_dis${k}_t07s1 $X --temperature 0.7 --seed 1 --distract $k > results/run_L_geox${m}_dis${k}.log 2>&1; done
  kill $S; }
lane Qwen3-8B 8069 q8b_large 8b & L1=$!
sleep 30
lane Qwen3-14B 8070 q14b_large 14b & L2=$!
sleep 30
lane Qwen3-32B-AWQ 8071 q32b_large 32b & L3=$!
wait $L1 $L2 $L3
echo REVIEW3_DONE >> results/queue_log.txt
