#!/bin/bash
# X7 (docs/prereg/PREREG_X7.md): MAMO held-out; hand-written vs automatic fact; 4 models on GPUs 0-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=mamo
lane() { g=$1 dir=$2 m=$3 port=$4 lo=$5 hi=$6
  tag=${m}_mamo; mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $g 0.88 x7_${m}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=14400 NLOPT_EX_TAG=$m
    tk="--think"; [ -n "$hi" ] && tk=""
    o() { mode=$1 sd=$2; shift 2; $P poc/run_nlopt.py $tag $mode $sd "$@" >> results/x3/run_${tag}_${mode}_s$sd.log 2>&1; }
    POC_REASONING_EFFORT=$lo o mip 1 --max_tokens 8192 &
    for sd in 1 2; do POC_REASONING_EFFORT=$lo o mipf $sd --max_tokens 8192 & POC_REASONING_EFFORT=$lo o mips $sd --max_tokens 8192 & done
    POC_REASONING_EFFORT=$hi o thinkf 1 $tk --max_tokens 16000 & POC_REASONING_EFFORT=$hi o thinks 1 $tk --max_tokens 16000 &
    wait
    kill $S; sleep 20
    n=$(cat results/x3/opt_${tag}_*_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 6041 ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_X7 $tag done ($n/6041) $(date)" >> results/queue_log.txt; }
lane 0 /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b 8107 "" "" &
lane 1 /SSD/huggingface/Qwen/Qwen3-14B-AWQ q14a 8108 "" "" &
lane 2 /SSD/huggingface/openai/gpt-oss-20b oss20 8109 low medium &
lane 3 /SSD/huggingface/Qwen/Qwen3-8B q8b 8110 "" "" &
wait
echo "S2_X7 runs done $(date)" >> results/queue_log.txt
