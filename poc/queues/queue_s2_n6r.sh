#!/bin/bash
# N6 replication: statement-retrieved exemplar, seeds 2-3, gpt-oss-120b low (8043) and gpt-oss-20b low (8042).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=low
for sd in 2 3; do POC_BASE_URL=http://127.0.0.1:8043/v1 $P poc/run_cc.py run oss120_low_ex_stmt $sd --exemplar stmt --max_tokens 16000 > results/h2/run_full_oss120_low_ex_stmt_s$sd.log 2>&1 & done
for sd in 2 3; do POC_BASE_URL=http://127.0.0.1:8042/v1 $P poc/run_cc.py run oss20_low_ex_stmt $sd --exemplar stmt --max_tokens 16000 > results/h2/run_full_oss20_low_ex_stmt_s$sd.log 2>&1 & done
wait
echo "S2_N6r runs done $(date)" >> results/queue_log.txt
