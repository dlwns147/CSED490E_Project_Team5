#!/bin/bash
# If a broad toolbox can't be trimmed and thinking is too costly: does verified sampling (MR-select over 3 K=8 samples) recover? Qwen3-8B/14B/32B,
# K=8 related helpers, seeds 2-3 (seed 1 = F_geox{m}_dis8_t07s1), n=300, --stdlib, T=0.7.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 2 3; do $P poc/run_geo_cross.py --model_tag F_geox${m}_dis8_t07s$sd --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed $sd --distract 8 > results/run_F_geox${m}_dis8_t07s$sd.log 2>&1; done; kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-8B 8090 q8b_d8mr 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8091 q14b_d8mr 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8092 q32b_d8mr 32b & L3=$!
wait $L1 $L2 $L3
echo DIS8MR_DONE >> results/queue_log.txt
