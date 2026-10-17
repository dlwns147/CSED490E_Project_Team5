#!/bin/bash
# E3b (docs/prereg/PREREG_E3B.md): brute-force reference programs, Qwen3-8B on 8040 (GPU 0), seed 1, no toolbox, C1 instances.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8040/v1
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1 --brute"
$P poc/run_geo_cross.py --model_tag S2_E3B_geox8b_brute_core_t07s1 $X > results/run_S2_E3B_core.log 2>&1 &
$P poc/run_geo_cross.py --model_tag S2_E3B_geox8b_brute_hard_t07s1 $X --tasks lattice,rectunion > results/run_S2_E3B_hard.log 2>&1 &
wait
echo "S2_E3B brute done $(date)" >> results/queue_log.txt
