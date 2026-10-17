#!/bin/bash
# VIEWS-P5 replication: PopQA views, Qwen3.6 on GPU3 (port 8063).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8063 3 0.88 x5_q36 --max-num-seqs 64 --language-model-only) || exit 1
export POC_BASE_URL=http://127.0.0.1:8063/v1
for v in "direct 1" "direct 2" "recall 1" "think 1"; do $P poc/run_popqa.py q36 $v > results/x5/run_q36_${v// /_}.log 2>&1 & done; wait
kill $S
$P poc/analyze_x5.py q36 > results/x5/analysis_q36.log 2>&1
echo "S2_X5b (PopQA views, Qwen3.6) done $(date)" >> results/queue_log.txt
