#!/bin/bash
# E4 pre-registered similarity test (results/PREREG_E4.md) on Qwen3-8B (GPU 0) and Qwen3-32B-AWQ (GPU 1); logit probe v2 runs on each server after.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
HI='{"hull": ["polar_sort", "collinear"], "area2": ["convex_hull", "is_convex"], "close": ["dist2", "bbox"]}'
LO='{"hull": ["segments_intersect", "point_in_polygon"], "area2": ["closest_pair_sq", "segments_intersect"], "close": ["polygon_area2", "is_convex"]}'
lane() { S=$(poc/start_server.sh /SSD/huggingface/Qwen/$1 $2 $3 0.45 $4) || { echo "$4 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$5; X="--tasks hull,area2,close --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --distract 0"
  for sd in 1 2; do
    $P poc/run_geo_cross.py --model_tag P_geox${m}_hi_t07s$sd $X --seed $sd --distract_set "$HI" > results/run_P_geox${m}_hi_s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag P_geox${m}_lo_t07s$sd $X --seed $sd --distract_set "$LO" > results/run_P_geox${m}_lo_s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag P_geox${m}_k0_t07s$sd $X --seed $sd > results/run_P_geox${m}_k0_s$sd.log 2>&1
  done
  $P poc/logit_probe2.py $m > results/logit_probe2_$m.txt 2>&1
  kill $S; }
lane Qwen3-8B 8093 0 q8b_e4 8b & L1=$!
sleep 30
lane Qwen3-32B-AWQ 8094 1 q32b_e4 32b & L2=$!
wait $L1 $L2
echo E4SIM_DONE >> results/queue_log.txt
