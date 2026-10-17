#!/bin/bash
# N5 + N2 baseline on Qwen3.8-27B no-think (q38_plain seed 1): N5 on 8046 (GPU0), N2 repair on 8048 (GPU1); shared with H6 runs.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
POC_BASE_URL=http://127.0.0.1:8046/v1 $P poc/oracle_cc.py all q38_plain 1 > results/h2/run_n5_q38_plain_s1.log 2>&1 &
POC_BASE_URL=http://127.0.0.1:8048/v1 $P poc/repair_cc.py q38_plain 1 > results/h2/run_rep_q38_plain_s1.log 2>&1 &
wait
echo "S2_N5 q38 runs done $(date)" >> results/queue_log.txt
