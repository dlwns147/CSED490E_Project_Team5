#!/bin/bash
# Review item 3 (toy scale): two realistic multi-step CG tasks added after all findings -
#   lattice  : integer points strictly inside a simple polygon (Pick: area + boundary gcd; polygon_area2 is the needed helper)
#   rectunion: area of the union of overlapping axis-aligned rectangles (sweep / coordinate compression; no needed helper)
# Qwen3 8B/14B/32B, --stdlib, n_inst 30 (120 programs per arm): greedy base; T=0.7 base x3 (MR-select); K=0/K=8 toolbox ("should" and neutral header);
# K=8 + thinking. Prefix R_.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--tasks lattice,rectunion --stdlib --n_inst 30 --max_tokens 4096"
  $P poc/run_geo_cross.py --model_tag R_geox${m}_base $X > results/run_R_geox${m}_base.log 2>&1
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag R_geox${m}_base_t07s$sd $X --temperature 0.7 --seed $sd > results/run_R_geox${m}_base_t07s$sd.log 2>&1; done
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag R_geox${m}_dis${k}_t07s1 $X --temperature 0.7 --seed 1 --distract $k > results/run_R_geox${m}_dis${k}.log 2>&1; done
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag R_geox${m}_dis${k}neu_t07s1 $X --temperature 0.7 --seed 1 --distract $k --tb_head neutral > results/run_R_geox${m}_dis${k}neu.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag R_geox${m}_base_think_t07s1 --tasks lattice,rectunion --stdlib --n_inst 30 --temperature 0.7 --seed 1 --think --max_tokens 20000 > results/run_R_geox${m}_base_think.log 2>&1
  $P poc/run_geo_cross.py --model_tag R_geox${m}_dis8think_t07s1 --tasks lattice,rectunion --stdlib --n_inst 30 --temperature 0.7 --seed 1 --distract 8 --think --max_tokens 20000 > results/run_R_geox${m}_dis8think.log 2>&1
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-8B 8075 q8b_real 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8076 q14b_real 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8077 q32b_real 32b & L3=$!
wait $L1 $L2 $L3
echo REAL_DONE >> results/queue_log.txt
