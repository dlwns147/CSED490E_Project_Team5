#!/bin/bash
# X6-VER2: the shortest check-passing program of the other benchmark as the fact; Qwen3-8B, GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_3 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8100 3 0.88 x6ver2_q8b_$att) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8100/v1 POC_TIMEOUT=14400
  for sd in 1 2 3; do
    $P poc/run_nlopt.py q8b mips $sd --max_tokens 8192 >> results/x3/run_q8b_mips_s$sd.log 2>&1 &
    $P poc/run_nlopt.py q8b thinks $sd --think --max_tokens 16000 >> results/x3/run_q8b_thinks_s$sd.log 2>&1 &
  done; wait
  kill $S; sleep 20
  n=$(cat results/x3/opt_q8b_mips_s*.jsonl results/x3/opt_q8b_thinks_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 2070 ] && break
done
rmdir results/.gpu_claim_3
echo "S2_X6VER2 q8b done ($n/2070) $(date)" >> results/queue_log.txt
