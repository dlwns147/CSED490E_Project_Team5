#!/bin/bash
# FORM (docs/prereg/PREREG_X7.md, 2026-10-19): formh (hand formulation sentence, TSP + redistribution) and formx (label-free cross-model
# mined program, all MAMO) for the 3090-class models, seeds 1-3. Lane A: GPU1 oss20 then q14a; lane B: GPU2 q8b (after INFEAS frees it).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=mamo
run() { g=$1 port=$2 dir=$3 m=$4 eff=$5
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh /SSD/huggingface/$dir $port $g 0.88 form_${m}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_REASONING_EFFORT=$eff NLOPT_EX_TAG=$m
    for sd in 1 2 3; do for md in formh formx; do $P poc/run_form.py $m $md $sd >> results/x3/run_form_${m}.log 2>&1 & done; done; wait
    kill $S; sleep 20
    n=$(cat results/x3/opt_${m}_mamo_form{h,x}_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 2739 ] && break
  done
  echo "S2_FORM $m done ($n/2739) $(date)" >> results/queue_log.txt; }
laneA() { mkdir results/.gpu_claim_1 || return 1; run 1 8124 openai/gpt-oss-20b oss20 low; run 1 8124 Qwen/Qwen3-14B-AWQ q14a ""; rmdir results/.gpu_claim_1; }
laneB() { for i in $(seq 720); do [ ! -d results/.gpu_claim_2 ] && [ "$(nvidia-smi -i 2 --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_2 && break; sleep 30; done
  run 2 8125 Qwen/Qwen3-8B q8b ""; rmdir results/.gpu_claim_2; }
echo "S2_FORM started $(date)" >> results/queue_log.txt
laneA & laneB & wait
echo "S2_FORM done $(date)" >> results/queue_log.txt
