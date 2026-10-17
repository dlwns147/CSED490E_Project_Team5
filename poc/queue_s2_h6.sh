#!/bin/bash
# H6 (results/PREREG_H6.md): Qwen3.8-27B-FP8. 8046 (GPU0): contest no-think x3, + 8 helpers x3, Solomon arms x2. 8047 (GPU3): contest full thinking x1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
( export POC_BASE_URL=http://127.0.0.1:8046/v1 CC_SET=full
  for sd in 1 2 3; do $P poc/run_cc.py run q38_plain $sd > results/h2/run_full_q38_plain_s$sd.log 2>&1; done
  for sd in 1 2 3; do $P poc/run_cc.py run q38_k8 $sd --k8 > results/h2/run_full_q38_k8_s$sd.log 2>&1; done
  for arm in plain docs parserintrobust; do fl=""; [ $arm = docs ] && fl=--snippet; [ $arm = parserintrobust ] && fl="--parser_int --snippet_robust"
    for sd in 1 2; do $P poc/run_solomon.py run q38_$arm $sd $fl > results/h3/run_q38_${arm}_s$sd.log 2>&1; done; done ) &
( export POC_BASE_URL=http://127.0.0.1:8047/v1 CC_SET=full
  $P poc/run_cc.py run q38_think 1 --think > results/h2/run_full_q38_think_s1.log 2>&1 ) &
wait
echo "S2_H6 runs done $(date)" >> results/queue_log.txt
