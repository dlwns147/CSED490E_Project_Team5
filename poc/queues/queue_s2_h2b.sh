#!/bin/bash
# H2b (docs/prereg/PREREG_H2B.md): extra samples (seeds 4-8) for selection. 8041 Qwen3-32B-AWQ, 8042 gpt-oss-20b low, 8043 gpt-oss-120b low.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
r() { port=$1 eff=$2 tag=$3 sd=$4; shift 4; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
      $P poc/run_cc.py run $tag $sd "$@" > results/h2/run_${tag}_s$sd.log 2>&1 ); }
for sd in 4 5 6 7 8; do
  r 8041 "" q32b_plain $sd & r 8042 low oss20_low $sd --max_tokens 16000 & r 8043 low oss120_low $sd --max_tokens 16000 &
done
wait
echo "S2_H2b runs done $(date)" >> results/queue_log.txt
