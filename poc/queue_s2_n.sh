#!/bin/bash
# N1/N2 (results/PREREG_N.md). 8040 Qwen3-32B-AWQ (GPU0, freed from full-thinking seeds 2-3): MEA transforms, contest repair, routing repair.
# 8042 gpt-oss-20b low (shared with H3b): contest repair, routing repair.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
( export POC_BASE_URL=http://127.0.0.1:8040/v1
  $P poc/mea_cc.py gen q32b > results/h2/run_mea_q32b.log 2>&1
  for sd in 1 2; do $P poc/repair_cc.py q32b_plain $sd > results/h2/run_rep_q32b_plain_s$sd.log 2>&1; done
  for sd in 1 2; do $P poc/run_solomon.py repair q32b_plain $sd > results/h3/run_rep_q32b_plain_s$sd.log 2>&1; done ) &
( export POC_BASE_URL=http://127.0.0.1:8042/v1 POC_REASONING_EFFORT=low
  for sd in 1 2; do $P poc/repair_cc.py oss20_low $sd --max_tokens 16000 > results/h2/run_rep_oss20_low_s$sd.log 2>&1; done
  for sd in 1 2; do $P poc/run_solomon.py repair oss20_low_plain $sd --max_tokens 16000 > results/h3/run_rep_oss20_low_plain_s$sd.log 2>&1; done ) &
wait
echo "S2_N runs done $(date)" >> results/queue_log.txt
