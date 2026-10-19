#!/bin/bash
# HO-L (docs/prereg/PREREG_HO.md): OptMATH with a solver-choice prompt (free / thinkfree); first free GPU of 1-2; oss20, q14a, q8b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=optmath POC_TIMEOUT=7200
G=""; for i in $(seq 720); do for g in 2 1; do
  [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$g 2>/dev/null && { G=$g; break 2; }; done; sleep 30; done
[ -n "$G" ] || exit 1
echo "S2_HOL started on GPU$G $(date)" >> results/queue_log.txt
for spec in "openai/gpt-oss-20b oss20 low medium" "Qwen/Qwen3-14B-AWQ q14a" "Qwen/Qwen3-8B q8b"; do
  set -- $spec; dir=$1 m=$2 lo=$3 hi=$4; tk="--think"; [ -n "$hi" ] && tk=""
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir 8129 $G 0.88 hol_$m) || continue
  export POC_BASE_URL=http://127.0.0.1:8129/v1
  for sd in 1 2 3; do
    POC_REASONING_EFFORT=$lo $P poc/run_nlopt.py ${m}_optmath free $sd --max_tokens 8192 >> results/x3/run_hol_${m}.log 2>&1 &
    POC_REASONING_EFFORT=$hi $P poc/run_nlopt.py ${m}_optmath thinkfree $sd $tk --max_tokens 16000 >> results/x3/run_hol_${m}.log 2>&1 &
  done; wait
  kill $S; sleep 20; echo "S2_HOL $m done $(date)" >> results/queue_log.txt
done
rmdir results/.gpu_claim_$G
echo "S2_HOL done $(date)" >> results/queue_log.txt
