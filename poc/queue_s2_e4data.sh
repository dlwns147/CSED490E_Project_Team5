#!/bin/bash
# E4 replay data: base Qwen3-8B WITHOUT thinking on the K0 (needed-helper) training prompts of the 5 non-core geometry tasks, the same
# instances / prompts as the thinking-teacher data T_geox8b_train2_k0_think (--inst_prefix train-, n_inst 60). Port 8044 (GPU 0).
cd /NAS/SJ/POSTECH/nlp
export POC_BASE_URL=http://127.0.0.1:8044/v1
/root/venvs/llm_algo_poc/bin/python poc/run_geo_cross.py --model_tag S2_E4_geox8b_train2_k0_nothink --tasks convex,tri,overlap,lattice,rectunion \
  --inst_prefix train- --save_prompt --stdlib --n_inst 60 --distract 0 --max_tokens 4096 --temperature 0.7 --seed 1 > results/run_S2_E4_data.log 2>&1
echo "S2_E4 data done $(date)" >> results/queue_log.txt
