#!/bin/bash
# OB (docs/prereg/PREREG_HO.md): second held-out benchmark OptiBench (605), solver-choice prompts free / thinkfree, seeds 1-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=optibench POC_TIMEOUT=7200
lane() { g=$1 port=$2; shift 2
  mkdir results/.gpu_claim_$g || return 1
  for spec in "$@"; do
    set -- $spec; dir=$1 m=$2 lo=$3 hi=$4; tk="--think"; [ -n "$hi" ] && tk=""
    S=$(bash poc/start_server.sh /SSD/huggingface/$dir $port $g 0.88 ob_$m) || continue
    for sd in 1 2 3; do
      POC_BASE_URL=http://127.0.0.1:$port/v1 POC_REASONING_EFFORT=$lo $P poc/run_nlopt.py ${m}_optibench free $sd --max_tokens 8192 >> results/x3/run_ob_${m}.log 2>&1 &
      POC_BASE_URL=http://127.0.0.1:$port/v1 POC_REASONING_EFFORT=$hi $P poc/run_nlopt.py ${m}_optibench thinkfree $sd $tk --max_tokens 16000 >> results/x3/run_ob_${m}.log 2>&1 &
    done; wait
    kill $S; sleep 20; echo "S2_OB $m done $(date)" >> results/queue_log.txt
  done
  rmdir results/.gpu_claim_$g; }
echo "S2_OB started $(date)" >> results/queue_log.txt
lane 0 8131 "openai/gpt-oss-20b oss20 low medium" "Qwen/Qwen3-8B q8b" & sleep 30
lane 1 8132 "Qwen/Qwen3-14B-AWQ q14a" & wait
echo "S2_OB done $(date)" >> results/queue_log.txt
