#!/bin/bash
# FORM2 (docs/prereg/PREREG_X7.md, 2026-10-19): formo (MAMO as a stream: only earlier problems' programs) and formx on NL4OPT + IndustryOR,
# 3090-class models, seeds 1-3. Lane A: GPU0 oss20 then q14a; lane B: GPU2 q8b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
run() { g=$1 port=$2 dir=$3 m=$4 eff=$5
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh /SSD/huggingface/$dir $port $g 0.88 form2_${m}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_REASONING_EFFORT=$eff NLOPT_EX_TAG=$m
    for sd in 1 2 3; do
      NLOPT_SET=mamo $P poc/run_form.py $m formo $sd >> results/x3/run_form2_${m}.log 2>&1 &
      NLOPT_SET=x3 $P poc/run_form.py $m formx $sd >> results/x3/run_form2_${m}.log 2>&1 &
    done; wait
    kill $S; sleep 20
    n=$(cat results/x3/opt_${m}_mamo_formo_s*.jsonl results/x3/opt_${m}_formx_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 3624 ] && break
  done
  echo "S2_FORM2 $m done ($n/3624) $(date)" >> results/queue_log.txt; }
laneA() { mkdir results/.gpu_claim_0 || return 1; run 0 8126 openai/gpt-oss-20b oss20 low; run 0 8126 Qwen/Qwen3-14B-AWQ q14a ""; rmdir results/.gpu_claim_0; }
laneB() { mkdir results/.gpu_claim_2 || return 1; run 2 8127 Qwen/Qwen3-8B q8b ""; rmdir results/.gpu_claim_2; }
echo "S2_FORM2 started $(date)" >> results/queue_log.txt
laneA & laneB & wait
echo "S2_FORM2 done $(date)" >> results/queue_log.txt
