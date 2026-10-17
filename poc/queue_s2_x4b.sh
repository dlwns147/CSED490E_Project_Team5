#!/bin/bash
# X4 stage 2 (PREREG_X3.md X4): gpt-oss-20b feedback round vs fresh sample on attempts naming unknown identifiers; then Qwen3-32B
# miniF2F generation with raw log-probs (k = 8) and checking. GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8053 2 0.88 x4b_oss20) || exit 1
POC_BASE_URL=http://127.0.0.1:8053/v1 POC_REASONING_EFFORT=low $P poc/run_lean.py fix oss20 test > results/x4/run_oss20_fix.log 2>&1
kill $S; sleep 25
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8053 2 0.88 x4b_q32b) || exit 1
POC_BASE_URL=http://127.0.0.1:8053/v1 $P poc/run_lean.py gen q32b test 8 --logprobs --max_tokens 8192 > results/x4/run_q32b_gen.log 2>&1
kill $S
$P poc/run_lean.py check results/x4/lean_q32b_test.jsonl > results/x4/run_q32b_check.log 2>&1
echo "S2_X4b (gpt-oss fix round + Qwen3-32B miniF2F) done $(date)" >> results/queue_log.txt
