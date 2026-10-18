#!/bin/bash
# Automatic facts, more models: Qwen3-32B shortest program (GPU0); Qwen3-14B-AWQ similar example + shortest program (GPU3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { g=$1 dir=$2 tag=$3 port=$4; shift 4; arms="$*"
  mkdir results/.gpu_claim_$g || return 1
  want=$(( 1035 * 2 * $(echo $arms | wc -w) ))
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $g 0.88 x6ver3_${tag}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=14400
    for a in $arms; do for sd in 1 2 3; do
      $P poc/run_nlopt.py $tag mip$a $sd --max_tokens 8192 >> results/x3/run_${tag}_mip${a}_s$sd.log 2>&1 &
      $P poc/run_nlopt.py $tag think$a $sd --think --max_tokens 16000 >> results/x3/run_${tag}_think${a}_s$sd.log 2>&1 &
    done; done; wait
    kill $S; sleep 20
    n=$(for a in $arms; do cat results/x3/opt_${tag}_mip${a}_s*.jsonl results/x3/opt_${tag}_think${a}_s*.jsonl 2>/dev/null; done | wc -l); [ "$n" -ge $want ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_X6VER3 $tag ($arms) done ($n/$want) $(date)" >> results/queue_log.txt; }
lane 0 /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b 8101 s &
lane 3 /SSD/huggingface/Qwen/Qwen3-14B-AWQ q14a 8102 v s &
wait
