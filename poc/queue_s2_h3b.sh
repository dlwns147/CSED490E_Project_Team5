#!/bin/bash
# H3b (results/PREREG_H3.md, H3b section): format fact (correct reader) arms. 8041 Qwen3-32B no-think, 8042 gpt-oss-20b low: parser arms.
# 8043 gpt-oss-120b low + medium (after their H2c Part B lanes): all six arms + words-only plain (medium).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
H=results/h2
waitf() { for f in "$@"; do while [ ! -s $H/cc_full_${f}_s3.jsonl ]; do sleep 60; done; done; }
lane() { port=$1 eff=$2 tag=$3 arms=$4; shift 4; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  for arm in $arms; do
    case $arm in plain) fl="";; docs) fl=--snippet;; robust) fl=--snippet_robust;; parser) fl=--parser;;
      parserdocs) fl="--parser --snippet";; parserrobust) fl="--parser --snippet_robust";; noexplain) fl=--noexample;; esac
    out=${tag}_$arm; [ $arm = noexplain ] && out=noex_${tag}_plain
    for sd in 1 2; do $P poc/run_solomon.py run $out $sd $fl "$@" > results/h3/run_${out}_s$sd.log 2>&1; done
  done ); }
lane 8041 "" q32b "parser parserdocs parserrobust" &
lane 8042 low oss20_low "parser parserdocs parserrobust" --max_tokens 16000 &
( waitf oss120_low oss120_medium
  lane 8043 low oss120_low "parser parserrobust plain docs robust parserdocs" --max_tokens 16000 &
  lane 8043 medium oss120_medium "parser parserrobust plain docs robust parserdocs noexplain" --max_tokens 16000 & wait ) &
wait
echo "S2_H3b runs done $(date)" >> results/queue_log.txt
