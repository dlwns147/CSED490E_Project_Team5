#!/bin/bash
# X7 addendum: Qwen3.6 on MAMO (cheap arms under q36_mamo, thinking 80k), GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=mamo NLOPT_EX_TAG=q36 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20 POC_TIMEOUT=14400
tag=q36_mamo; mkdir results/.gpu_claim_2 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8111 2 0.88 x7_q36_$att --max-num-seqs 64 --language-model-only --max-model-len 90000) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8111/v1
  o() { mode=$1 sd=$2; shift 2; $P poc/run_nlopt.py $tag $mode $sd "$@" >> results/x3/run_${tag}_${mode}_s$sd.log 2>&1; }
  o mip 1 --max_tokens 8192 &
  for sd in 1 2; do o mipf $sd --max_tokens 8192 & o mips $sd --max_tokens 8192 & done
  o thinkf 1 --think --max_tokens 80000 & o thinks 1 --think --max_tokens 80000 &
  wait; kill $S; sleep 20
  n=$(cat results/x3/opt_${tag}_*_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 6041 ] && break
done
rmdir results/.gpu_claim_2
echo "S2_X7 $tag done ($n/6041) $(date)" >> results/queue_log.txt
