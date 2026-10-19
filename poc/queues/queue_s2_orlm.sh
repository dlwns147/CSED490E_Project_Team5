#!/bin/bash
# ORLM baseline: X3 set and MAMO, seeds 1 (greedy) and 2-3 (T 0.7); first free GPU among 0-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
G=""; for i in $(seq 1440); do for g in 3 1 0 2; do
  [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$g 2>/dev/null && { G=$g; break 2; }; done; sleep 20; done
[ -n "$G" ] || exit 1
echo "S2_ORLM started on GPU$G $(date)" >> results/queue_log.txt
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/CardinalOperations/ORLM-LLaMA-3-8B 8115 $G 0.88 orlm_$att --max-model-len 8192) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8115/v1
  for sd in 1 2 3; do
    $P poc/run_orlm.py orlm $sd >> results/x3/run_orlm_s$sd.log 2>&1 &
    NLOPT_SET=mamo $P poc/run_orlm.py orlm_mamo $sd >> results/x3/run_orlm_mamo_s$sd.log 2>&1 &
  done; wait
  kill $S; sleep 20
  n=$(cat results/x3/opt_orlm_orlm_s*.jsonl results/x3/opt_orlm_mamo_orlm_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 3624 ] && break
done
rmdir results/.gpu_claim_$G
echo "S2_ORLM done ($n/3624) $(date)" >> results/queue_log.txt
