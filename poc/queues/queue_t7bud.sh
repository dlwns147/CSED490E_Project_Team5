#!/bin/bash
# T7 follow-ups (hard tasks lattice + rectunion, n_inst 30 = 120 programs/arm):
#  (a) reasoning in another family: DeepSeek-R1-Distill-Llama-70B (GPU 3, 0.7; T=0.6, max_tokens 16000): no toolbox / K8 (Llama-70B: 0-1 / 45 of 60 lattice)
#  (b) X1 on hard tasks: budget-forced thinking B = 1024 / 2048 / 4096 for Qwen3-8B (GPU 0) and Qwen3-32B-AWQ (GPU 1), no toolbox, T=0.7 s1
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
T="--tasks lattice,rectunion --stdlib --n_inst 30"
r1() { S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/DeepSeek-R1-Distill-Llama-70B-quantized.w4a16 8083 3 0.7 r1l70_t7) || { echo "r1l70_t7 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:8083/v1; X="$T --max_tokens 16000 --temperature 0.6 --seed 1"
  $P poc/run_geo_cross.py --model_tag R_geoxr1l70_base_t06s1 $X > results/run_R_geoxr1l70_base.log 2>&1
  $P poc/run_geo_cross.py --model_tag R_geoxr1l70_dis8_t06s1 $X --distract 8 > results/run_R_geoxr1l70_dis8.log 2>&1
  kill $S; }
bud() { S=$(poc/start_server.sh /SSD/huggingface/Qwen/$1 $2 $3 0.45 $4) || { echo "$4 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1
  for B in 1024 2048 4096; do $P poc/run_geo_cross.py --model_tag R_geox$5_base_b$B $T --max_tokens 4096 --temperature 0.7 --seed 1 --think_budget $B > results/run_R_geox$5_b$B.log 2>&1; done
  kill $S; }
r1 & L1=$!
bud Qwen3-8B 8084 0 q8b_t7bud 8b & L2=$!
sleep 30
bud Qwen3-32B-AWQ 8085 1 q32b_t7bud 32b & L3=$!
wait $L1 $L2 $L3
echo T7BUD_DONE >> results/queue_log.txt
