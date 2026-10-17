#!/bin/bash
# X1 Qwen3-32B thinking: when queue_s2_rerun_think2.sh logs its end (<= 3 h), regrade the three files and run analyze_x1.py q32b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 540); do grep -q "^S2_X1 q32b thinking:" results/queue_log.txt && break; sleep 20; done
grep -q "^S2_X1 q32b thinking:" results/queue_log.txt || { echo "S2_X1fin waiter gave up $(date)" >> results/queue_log.txt; exit 1; }
timeout 3600 $P poc/run_math.py --regrade results/x1/math_q32b_think_s1.jsonl results/x1/math_q32b_think_s2.jsonl results/x1/math_q32b_think_s3.jsonl > results/x1/regrade_q32b_think.log 2>&1
timeout 3600 $P poc/analyze_x1.py q32b > results/x1/analysis_q32b.log 2>&1
echo "S2_X1fin regrade + analysis done $(date)" >> results/queue_log.txt
