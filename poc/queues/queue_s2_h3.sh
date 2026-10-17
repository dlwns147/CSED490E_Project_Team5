#!/bin/bash
# H3 (docs/prereg/PREREG_H3.md): Solomon VRPTW. Each server lane starts when its H2c Part B lanes have written their seed-3 files.
# 8041 Qwen3-32B-AWQ (no-think), 8042 gpt-oss-20b low, 8043 gpt-oss-120b low + medium. Arms: plain, docs snippet, robust snippet; seeds 1-2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
H=results/h2
waitf() { for f in "$@"; do while [ ! -s $H/cc_full_${f}_s3.jsonl ]; do sleep 60; done; done; }
lane() { port=$1 eff=$2 tag=$3; shift 3; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  for arm in plain docs robust; do
    fl=""; [ $arm = docs ] && fl=--snippet; [ $arm = robust ] && fl=--snippet_robust
    for sd in 1 2; do $P poc/run_solomon.py run ${tag}_$arm $sd $fl "$@" > results/h3/run_${tag}_${arm}_s$sd.log 2>&1; done
  done
  if [ "$tag" = oss120_medium ]; then for sd in 1 2; do $P poc/run_solomon.py run noex_${tag}_plain $sd --noexample "$@" > results/h3/run_noex_${tag}_plain_s$sd.log 2>&1; done; fi ); }
( waitf q32b_plain q32b_think1024; lane 8041 "" q32b ) &
( waitf oss20_low oss20_medium; lane 8042 low oss20_low --max_tokens 16000 ) &
( waitf oss120_low oss120_medium; lane 8043 low oss120_low --max_tokens 16000 & lane 8043 medium oss120_medium --max_tokens 16000 & wait ) &
wait
echo "S2_H3 runs done $(date)" >> results/queue_log.txt
