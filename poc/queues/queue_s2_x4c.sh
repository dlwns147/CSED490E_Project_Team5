#!/bin/bash
# X4-P2b: feedback with similar existing Mathlib names + types, gpt-oss-20b low on GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8054 2 0.88 x4c_oss20) || exit 1
POC_BASE_URL=http://127.0.0.1:8054/v1 POC_REASONING_EFFORT=low $P poc/lean_factfix.py oss20 test > results/x4/run_oss20_factfix.log 2>&1
kill $S
echo "S2_X4c (miniF2F fact feedback) done $(date)" >> results/queue_log.txt
