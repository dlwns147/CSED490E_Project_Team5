#!/bin/bash
# HO (docs/prereg/PREREG_HO.md): held-out OptMATH-Bench, 24 GB-GPU models on GPU0, sequentially; then the library arm (needs all mips runs).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=optmath POC_TIMEOUT=7200
mkdir results/.gpu_claim_0 || exit 1
echo "S2_HO started on GPU0 $(date)" >> results/queue_log.txt
srv() { bash poc/start_server.sh /SSD/huggingface/$1 8128 0 0.88 ho_$2; }
for spec in "openai/gpt-oss-20b oss20 low medium" "Qwen/Qwen3-14B-AWQ q14a" "Qwen/Qwen3-8B q8b"; do
  set -- $spec; dir=$1 m=$2 lo=$3 hi=$4; tk="--think"; [ -n "$hi" ] && tk=""
  S=$(srv $dir $m) || { echo "S2_HO $m server failed $(date)" >> results/queue_log.txt; continue; }
  export POC_BASE_URL=http://127.0.0.1:8128/v1 NLOPT_EX_TAG=$m
  o() { mode=$1 sd=$2; shift 2; $P poc/run_nlopt.py ${m}_optmath $mode $sd "$@" >> results/x3/run_ho_${m}.log 2>&1; }
  POC_REASONING_EFFORT=$lo o mip 1 --max_tokens 8192 & POC_REASONING_EFFORT=$lo o mipf 1 --max_tokens 8192 &
  for sd in 1 2 3; do POC_REASONING_EFFORT=$lo o mips $sd --max_tokens 8192 & POC_REASONING_EFFORT=$hi o thinks $sd $tk --max_tokens 16000 & done; wait
  kill $S; sleep 20
  echo "S2_HO $m arms done $(date)" >> results/queue_log.txt
done
for spec in "openai/gpt-oss-20b oss20 low" "Qwen/Qwen3-14B-AWQ q14a" "Qwen/Qwen3-8B q8b"; do   # library arm
  set -- $spec; dir=$1 m=$2 lo=$3
  S=$(srv $dir ${m}_lib) || continue
  export POC_BASE_URL=http://127.0.0.1:8128/v1 NLOPT_EX_TAG=$m
  for sd in 1 2 3; do POC_REASONING_EFFORT=$lo $P poc/run_form.py $m formx $sd >> results/x3/run_ho_${m}.log 2>&1 & done; wait
  kill $S; sleep 20
done
rmdir results/.gpu_claim_0
echo "S2_HO done $(date)" >> results/queue_log.txt
