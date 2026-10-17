#!/bin/bash
# H4 (docs/prereg/PREREG_H4.md): 8 related helpers on the full contest-geometry set. 8040 Qwen3-32B-AWQ, 8042 gpt-oss-20b low.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
( export POC_BASE_URL=http://127.0.0.1:8040/v1; for sd in 1 2 3; do $P poc/run_cc.py run q32b_k8 $sd --k8 > results/h2/run_full_q32b_k8_s$sd.log 2>&1; done ) &
( export POC_BASE_URL=http://127.0.0.1:8042/v1 POC_REASONING_EFFORT=low
  for sd in 1 2 3; do $P poc/run_cc.py run oss20_low_k8 $sd --k8 --max_tokens 16000 > results/h2/run_full_oss20_low_k8_s$sd.log 2>&1; done ) &
wait
echo "S2_H4 runs done $(date)" >> results/queue_log.txt
