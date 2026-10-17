#!/bin/bash
# V1c (PREREG_V.md): 48 more mining-instance candidates for Qwen3-32B-AWQ no-think, plain and + docs (8041 GPU0).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8041 0 0.88 v1c_q32b) || exit 1
export POC_BASE_URL=http://127.0.0.1:8041/v1 SOLOMON_ONLY=c101,c201,r101,r201,rc101,rc201,r105,rc105
for sd in 3 4 5 6 7 8; do
  $P poc/run_solomon.py run q32b_plain $sd > results/h3/run_q32b_plain_s$sd.log 2>&1 &
  $P poc/run_solomon.py run q32b_docs $sd --snippet > results/h3/run_q32b_docs_s$sd.log 2>&1 &
  wait
done
kill $S
echo "S2_V1c generation done $(date)" >> results/queue_log.txt
