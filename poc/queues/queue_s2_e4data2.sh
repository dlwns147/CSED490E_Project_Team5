#!/bin/bash
# E4 replay data, extra student seeds 2-6 for the tasks where the no-thinking 8B is rarely correct (tri, lattice, rectunion) + convex.
cd /NAS/SJ/POSTECH/nlp
export POC_BASE_URL=http://127.0.0.1:8044/v1
for sd in 2 3 4 5 6; do
  /root/venvs/llm_algo_poc/bin/python poc/run_geo_cross.py --model_tag S2_E4_geox8b_train2_k0_nothink_s$sd --tasks convex,tri,lattice,rectunion \
    --inst_prefix train- --save_prompt --stdlib --n_inst 60 --distract 0 --max_tokens 4096 --temperature 0.7 --seed $sd > results/run_S2_E4_data_s$sd.log 2>&1 &
done
wait
echo "S2_E4 data2 done $(date)" >> results/queue_log.txt
