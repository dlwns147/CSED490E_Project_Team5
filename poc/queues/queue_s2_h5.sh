#!/bin/bash
# H5 (docs/prereg/PREREG_H5.md): job-shop la01-la40, no facts. 8045 gpt-oss-120b (GPU0) low; gpt-oss-20b low on 8042 after its FM2g queue.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low
( export POC_BASE_URL=http://127.0.0.1:8045/v1; for sd in 1 2; do $P poc/run_jssp.py run oss120_low_plain $sd --max_tokens 16000 > results/h5/run_oss120_low_plain_s$sd.log 2>&1; done ) &
( while ! grep -q "S2_FM2g runs done" results/queue_log.txt; do sleep 60; done
  export POC_BASE_URL=http://127.0.0.1:8042/v1; for sd in 1 2; do $P poc/run_jssp.py run oss20_low_plain $sd --max_tokens 16000 > results/h5/run_oss20_low_plain_s$sd.log 2>&1; done ) &
wait
echo "S2_H5 runs done $(date)" >> results/queue_log.txt
