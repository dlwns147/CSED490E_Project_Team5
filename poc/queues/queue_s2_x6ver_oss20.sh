#!/bin/bash
# Automatic facts for gpt-oss-20b: mined similar example (v) and shortest program (s); low effort for the cheap arm, medium for thinking; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_2 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8103 2 0.88 x6ver_oss20_$att) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8103/v1 POC_TIMEOUT=14400
  for a in v s; do for sd in 1 2 3; do
    POC_REASONING_EFFORT=low $P poc/run_nlopt.py oss20 mip$a $sd --max_tokens 16000 >> results/x3/run_oss20_mip${a}_s$sd.log 2>&1 &
    POC_REASONING_EFFORT=medium $P poc/run_nlopt.py oss20 think$a $sd --max_tokens 16000 >> results/x3/run_oss20_think${a}_s$sd.log 2>&1 &
  done; done; wait
  kill $S; sleep 20
  n=$(cat results/x3/opt_oss20_mip[vs]_s*.jsonl results/x3/opt_oss20_think[vs]_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 4140 ] && break
done
rmdir results/.gpu_claim_2
echo "S2_X6VER oss20 (v, s) done ($n/4140) $(date)" >> results/queue_log.txt
