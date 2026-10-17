#!/bin/bash
# FM3 (PREREG_FM.md): pool chains C-H, prune on the mining set (8043), then test pruned (8043) and raw pool (8044) sheets.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low
POC_BASE_URL=http://127.0.0.1:8043/v1 $P poc/fact_mine.py pool P C D E F G H --max_tokens 16000 > results/h3/run_fm_pool_P.log 2>&1
( export POC_BASE_URL=http://127.0.0.1:8043/v1; for sd in 1 2; do $P poc/fact_mine.py test P verified $sd --max_tokens 16000 > results/h3/run_fm_P_verified_s$sd.log 2>&1; done ) &
( export POC_BASE_URL=http://127.0.0.1:8044/v1; for sd in 1 2; do $P poc/fact_mine.py test P unverified $sd --max_tokens 16000 > results/h3/run_fm_P_unverified_s$sd.log 2>&1; done ) &
wait
echo "S2_FM3 runs done $(date)" >> results/queue_log.txt
