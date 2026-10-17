#!/bin/bash
# X6 (docs/prereg/PREREG_X3.md): Qwen3-32B thinking + API snippet (thinkf) on X3, seeds 1-3. Waits (<= 5 h) until the X1 q32b re-run
# (queue_s2_rerun_think2.sh) has logged its end and GPU1 is empty, then regrades + analyzes X1 q32b (CPU) and runs X6 on GPU1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 900); do
  grep -q "^S2_X1 q32b thinking:" results/queue_log.txt && \
    [ "$(nvidia-smi -i 1 --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && break
  sleep 20; done
[ "$(nvidia-smi -i 1 --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] || { echo "S2_X6 waiter gave up $(date)" >> results/queue_log.txt; exit 1; }
echo "S2_X6 started (GPU1, port 8062) $(date)" >> results/queue_log.txt
( timeout 3600 $P poc/run_math.py --regrade results/x1/math_q32b_think_s1.jsonl results/x1/math_q32b_think_s2.jsonl results/x1/math_q32b_think_s3.jsonl > results/x1/regrade_q32b_think.log 2>&1
  timeout 3600 $P poc/analyze_x1.py q32b > results/x1/analysis_q32b.log 2>&1 ) &
for att in 1 2 3 4; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8062 1 0.88 x6_q32b_$att) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8062/v1
  for sd in 1 2 3; do $P poc/run_nlopt.py q32b thinkf $sd --think --max_tokens 16000 >> results/x3/run_q32b_thinkf_s$sd.log 2>&1 & done; wait
  kill $S; sleep 20
  n=$(cat results/x3/opt_q32b_thinkf_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 1035 ] && break
done
echo "S2_X6 done ($n/1035 rows) $(date)" >> results/queue_log.txt
