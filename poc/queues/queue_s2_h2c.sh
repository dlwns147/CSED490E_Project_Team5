#!/bin/bash
# H2c Part B (docs/prereg/PREREG_H2C.md): full contest-geometry set (CC_SET=full). 8040 Qwen3-32B-AWQ (GPU0, full thinking),
# 8041 Qwen3-32B-AWQ (GPU1, no-think + think-1,024), 8042 gpt-oss-20b, 8043 gpt-oss-120b. One lane per condition, seeds in order.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
while [ ! -s results/h2/cc_valid_full.json ]; do sleep 30; done
r() { port=$1 eff=$2 tag=$3; shift 3; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
      for sd in 1 2 3; do $P poc/run_cc.py run $tag $sd "$@" > results/h2/run_full_${tag}_s$sd.log 2>&1; done ); }
r 8040 "" q32b_think --think &
r 8041 "" q32b_plain & r 8041 "" q32b_think1024 --think_budget 1024 &
r 8042 low oss20_low --max_tokens 16000 & r 8042 medium oss20_medium --max_tokens 16000 &
r 8043 low oss120_low --max_tokens 16000 & r 8043 medium oss120_medium --max_tokens 16000 &
wait
echo "S2_H2c runs done $(date)" >> results/queue_log.txt
