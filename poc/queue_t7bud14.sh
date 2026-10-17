#!/bin/bash
# X1 on hard tasks, 14B: budget-forced thinking B = 1024 / 2048 / 4096 (GPU 0), lattice + rectunion, no toolbox, T=0.7 s1
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-14B 8086 0 0.45 q14b_t7bud) || { echo "q14b_t7bud failed" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8086/v1
for B in 1024 2048 4096; do $P poc/run_geo_cross.py --model_tag R_geox14b_base_b$B --tasks lattice,rectunion --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1 --think_budget $B > results/run_R_geox14b_b$B.log 2>&1; done
kill $S
echo T7BUD14_DONE >> results/queue_log.txt
