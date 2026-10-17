#!/bin/bash
# VIEWS-P5: PopQA views, Qwen3-8B on GPU3 (port 8062).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8062 3 0.88 x5_q8b) || exit 1
export POC_BASE_URL=http://127.0.0.1:8062/v1
$P poc/run_popqa.py q8b direct 1 > results/x5/run_direct_1.log 2>&1 & $P poc/run_popqa.py q8b direct 2 > results/x5/run_direct_2.log 2>&1 &
$P poc/run_popqa.py q8b recall 1 > results/x5/run_recall_1.log 2>&1 & $P poc/run_popqa.py q8b think 1 > results/x5/run_think_1.log 2>&1 &
wait; kill $S
echo "S2_X5 (PopQA views, Qwen3-8B) done $(date)" >> results/queue_log.txt
