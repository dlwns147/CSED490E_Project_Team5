#!/bin/bash
# Mechanism split of the distractor harm: helpers PRE-DEFINED at execution ("prelude": no copy step, so no NameErrors from uncopied helpers) vs the copy-in
# header. K = 0 / 8, --stdlib, n_inst 30 (300 programs), T=0.7 seed 1. Existing: F_geox{m}_dis8_t07s1 (copy, K=8).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  $P poc/run_geo_cross.py --model_tag F_geox${m}_dis0_t07s1 $X --distract 0 > results/run_F_geox${m}_dis0_t07s1.log 2>&1
  $P poc/run_geo_cross.py --model_tag F_geox${m}_dis0pre_t07s1 $X --distract 0 --tb_head prelude > results/run_F_geox${m}_dis0pre_t07s1.log 2>&1
  $P poc/run_geo_cross.py --model_tag F_geox${m}_dis8pre_t07s1 $X --distract 8 --tb_head prelude > results/run_F_geox${m}_dis8pre_t07s1.log 2>&1
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8059 q8b_pre 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8060 q14b_pre 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8061 q32b_pre 32b & L3=$!
wait $L1 $L2 $L3
echo PRELUDE_DONE >> results/queue_distract.log
