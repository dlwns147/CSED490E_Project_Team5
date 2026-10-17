#!/bin/bash
# Final, properly powered geometry table with the environment fact (--stdlib): n_inst=30 per size (300 programs per run, 3x the PoC).
# Per model: greedy base / task-matched; T=0.7 base x3 seeds (MR-select k=3); T=0.7 task-matched x1; T=0.7 K=8 related distractors x1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--stdlib --n_inst 30 --max_tokens 4096"
  $P poc/run_geo_cross.py --model_tag F_geox${m}_base $X > results/run_F_geox${m}_base.log 2>&1
  $P poc/run_geo_cross.py --model_tag F_geox${m}_pt $X --primitives --prims_task > results/run_F_geox${m}_pt.log 2>&1
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag F_geox${m}_base_t07s$sd $X --temperature 0.7 --seed $sd > results/run_F_geox${m}_base_t07s$sd.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag F_geox${m}_pt_t07s1 $X --primitives --prims_task --temperature 0.7 --seed 1 > results/run_F_geox${m}_pt_t07s1.log 2>&1
  $P poc/run_geo_cross.py --model_tag F_geox${m}_dis8_t07s1 $X --distract 8 --temperature 0.7 --seed 1 > results/run_F_geox${m}_dis8_t07s1.log 2>&1
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8044 q8b_final 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8045 q14b_final 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8046 q32b_final 32b & L3=$!
wait $L1 $L2 $L3
echo FINALGEO_DONE >> results/queue_distract.log
