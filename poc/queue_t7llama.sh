#!/bin/bash
# Review item 5 (model coverage) on T7: does the capability gate and the signed-area trap hold for another family?
# Llama-3.3-70B-w4a16 (GPU 3, 0.7) and Llama-3.1-8B (GPU 0, 0.45); lattice + rectunion, --stdlib, n_inst 30, T=0.7.
# arms: no toolbox s1-3 (MR-select), K0 signed / abs helper, K8 "should", K8 prelude (helpers pre-defined: no copy failures).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { S=$(poc/start_server.sh $1 $2 $3 $4 $5) || { echo "$5 failed to start" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$6; X="--tasks lattice,rectunion --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag L_geox${m}_base_t07s$sd $X --seed $sd > results/run_L_geox${m}_base_s$sd.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag L_geox${m}_dis0_t07s1 $X --seed 1 --distract 0 > results/run_L_geox${m}_dis0.log 2>&1
  $P poc/run_geo_cross.py --model_tag L_geox${m}_dis0abs_t07s1 $X --seed 1 --distract 0 --area_helper abs > results/run_L_geox${m}_dis0abs.log 2>&1
  $P poc/run_geo_cross.py --model_tag L_geox${m}_dis8_t07s1 $X --seed 1 --distract 8 > results/run_L_geox${m}_dis8.log 2>&1
  $P poc/run_geo_cross.py --model_tag L_geox${m}_dis8pre_t07s1 $X --seed 1 --distract 8 --tb_head prelude > results/run_L_geox${m}_dis8pre.log 2>&1
  kill $S; }
lane /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8081 3 0.7 llama70_t7 l70 & L1=$!
sleep 60
lane /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8082 0 0.45 llama8_t7 l8 & L2=$!
wait $L1 $L2
echo T7LLAMA_DONE >> results/queue_log.txt
