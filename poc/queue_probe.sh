#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-8B 8029 q8b_probe 9>&-) || exit 1
POC_BASE_URL=http://127.0.0.1:8029/v1 $P $1 > results/probe_tsp8b.log 2>&1
kill $S
