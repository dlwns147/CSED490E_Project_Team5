#!/bin/bash
# X7 replication for Qwen3-8B (GPU3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=mamo
lane() { g=$1 dir=$2 m=$3 port=$4 lo=$5 hi=$6
  tag=${m}_mamo; mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $g 0.88 x7rep_${m}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=14400 NLOPT_EX_TAG=$m
    tk="--think"; [ -n "$hi" ] && tk=""
    o() { mode=$1 sd=$2; shift 2; $P poc/run_nlopt.py $tag $mode $sd "$@" >> results/x3/run_${tag}_${mode}_s$sd.log 2>&1; }
    POC_REASONING_EFFORT=$lo o mipf 3 --max_tokens 8192 & POC_REASONING_EFFORT=$lo o mips 3 --max_tokens 8192 &
    for sd in 2 3; do POC_REASONING_EFFORT=$hi o thinkf $sd $tk --max_tokens 16000 & POC_REASONING_EFFORT=$hi o thinks $sd $tk --max_tokens 16000 & done
    wait; kill $S; sleep 20
    n=$(cat results/x3/opt_${tag}_mipf_s3.jsonl results/x3/opt_${tag}_mips_s3.jsonl results/x3/opt_${tag}_think[fs]_s[23].jsonl 2>/dev/null | wc -l); [ "$n" -ge 5178 ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_X7REP $tag done ($n/5178) $(date)" >> results/queue_log.txt; }
lane 3 /SSD/huggingface/Qwen/Qwen3-8B q8b 8114 "" ""
