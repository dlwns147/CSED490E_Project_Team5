#!/bin/bash
# H6c (PREREG_H6.md): Qwen3.8 with a 28k cap, seed 1. 8046 (GPU0) no-think, 8049 (GPU2) thinking effort low.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
POC_BASE_URL=http://127.0.0.1:8046/v1 $P poc/run_cc.py run q38_plain28k 1 --max_tokens 28000 > results/h2/run_full_q38_plain28k_s1.log 2>&1 &
POC_BASE_URL=http://127.0.0.1:8049/v1 POC_TEMPLATE_EFFORT=low $P poc/run_cc.py run q38_thinklow28k 1 --think --max_tokens 28000 > results/h2/run_full_q38_thinklow28k_s1.log 2>&1 &
wait
echo "S2_H6c runs done $(date)" >> results/queue_log.txt
