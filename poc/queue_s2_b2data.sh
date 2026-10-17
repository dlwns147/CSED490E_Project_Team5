#!/bin/bash
# B2 self-SFT data: the student's own no-thinking programs on the 4 trained tasks, training prompts K0/K4/K8 (as the teacher data). 8040.
cd /NAS/SJ/POSTECH/nlp
export POC_BASE_URL=http://127.0.0.1:8040/v1
for k in 0 4 8; do
  /root/venvs/llm_algo_poc/bin/python poc/run_geo_cross.py --model_tag S2_B2_geox8b_train_k${k}_nothink --tasks area2,pip,segs,close --inst_prefix train- \
    --save_prompt --stdlib --n_inst 60 --distract $k --max_tokens 4096 --temperature 0.7 --seed 1 > results/run_S2_B2_selfsft_k$k.log 2>&1 &
done
wait
echo "S2_B2 selfsft data done $(date)" >> results/queue_log.txt
