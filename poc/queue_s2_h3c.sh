#!/bin/bash
# H3c (integer reader, PREREG_H3.md) + N2b (repair for gpt-oss-120b low and Qwen think-1,024, PREREG_N.md).
# 8040 Qwen3-32B-AWQ (GPU0), 8042 gpt-oss-20b (GPU2), 8044 gpt-oss-120b (GPU1). 8043 keeps running H3b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
h3() { port=$1 eff=$2 tag=$3; shift 3; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  for arm in parserint parserintrobust; do fl=--parser_int; [ $arm = parserintrobust ] && fl="--parser_int --snippet_robust"
    for sd in 1 2; do $P poc/run_solomon.py run ${tag}_$arm $sd $fl "$@" > results/h3/run_${tag}_${arm}_s$sd.log 2>&1; done; done ); }
( h3 8040 "" q32b
  POC_BASE_URL=http://127.0.0.1:8040/v1 CC_SET=full $P poc/repair_cc.py q32b_think1024 1 --think_budget 1024 > results/h2/run_rep_q32b_think1024_s1.log 2>&1 ) &
h3 8042 low oss20_low --max_tokens 16000 &
( for sd in 1 2; do POC_BASE_URL=http://127.0.0.1:8044/v1 POC_REASONING_EFFORT=low CC_SET=full $P poc/repair_cc.py oss120_low $sd --max_tokens 16000 \
      > results/h2/run_rep_oss120_low_s$sd.log 2>&1; done
  h3 8044 low oss120_low --max_tokens 16000 & h3 8044 medium oss120_medium --max_tokens 16000 & wait ) &
wait
echo "S2_H3c runs done $(date)" >> results/queue_log.txt
