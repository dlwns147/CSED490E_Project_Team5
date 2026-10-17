#!/bin/bash
# Server 2, C1 (pre-registered in FINDINGS 2026-10-13 12:15): confidence (token log-probs) as a label-free selector.
# Qwen3-8B on port 8044 (GPU 0, shared with gpt-oss-20b). No thinking, --stdlib, T=0.7, seeds 1-3; K0 / K8 core tasks (300 each) and the
# hard tasks lattice + rectunion without a toolbox (120 each). Tags S2_C1_geox8b_{dis0,dis8,hard}_t07s<seed> (mr_select.py naming).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:${PORT:-8044}/v1
M=${M:-8b}
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --logprobs"
for sd in 1 2 3; do
  $P poc/run_geo_cross.py --model_tag S2_C1_geox${M}_dis0_t07s$sd $X --seed $sd --distract 0 > results/run_S2_C1_geox${M}_dis0_t07s$sd.log 2>&1 &
  $P poc/run_geo_cross.py --model_tag S2_C1_geox${M}_dis8_t07s$sd $X --seed $sd --distract 8 > results/run_S2_C1_geox${M}_dis8_t07s$sd.log 2>&1 &
  $P poc/run_geo_cross.py --model_tag S2_C1_geox${M}_hard_t07s$sd $X --seed $sd --tasks lattice,rectunion > results/run_S2_C1_geox${M}_hard_t07s$sd.log 2>&1 &
  wait   # only this script's own three runs are children here
done
echo "S2_C1 $M done $(date)" >> results/queue_log.txt
