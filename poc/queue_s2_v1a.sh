#!/bin/bash
# V1A (PREREG_V.md): Qwen3-8B (8040 GPU0) and Qwen3-32B-AWQ (8041 GPU1) write brute-force oracles; label-free reuse on synthetic tasks.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S0=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8040 0 0.85 v1a_8b) && (POC_BASE_URL=http://127.0.0.1:8040/v1 $P poc/reuse_oracle_geo.py 8b > results/reuse_v1a_8b.log 2>&1; kill $S0) &
S1=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8041 1 0.88 v1a_32b) && (POC_BASE_URL=http://127.0.0.1:8041/v1 $P poc/reuse_oracle_geo.py 32b > results/reuse_v1a_32b.log 2>&1; kill $S1) &
wait
echo "S2_V1A runs done $(date)" >> results/queue_log.txt
