#!/bin/bash
# H4b (PREREG_H4.md): 8042 gpt-oss-20b low: unrelated helpers / related helpers with the "may" header; 8044 gpt-oss-120b low: related helpers.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=low
r() { port=$1 tag=$2; shift 2; ( export POC_BASE_URL=http://127.0.0.1:$port/v1
  for sd in 1 2 3; do $P poc/run_cc.py run $tag $sd "$@" --max_tokens 16000 > results/h2/run_full_${tag}_s$sd.log 2>&1; done ); }
r 8042 oss20_low_k8u --k8u & r 8042 oss20_low_k8may --k8may & r 8044 oss120_low_k8 --k8 &
wait
echo "S2_H4b runs done $(date)" >> results/queue_log.txt
