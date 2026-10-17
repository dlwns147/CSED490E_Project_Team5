#!/bin/bash
# X4 (PREREG_X3.md): miniF2F whole-proof generation, gpt-oss-20b low on GPU2, then Lean checking on CPU.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8053 2 0.88 x4_oss20) || exit 1
POC_BASE_URL=http://127.0.0.1:8053/v1 POC_REASONING_EFFORT=low $P poc/run_lean.py gen oss20 test 8 --max_tokens 16000 > results/x4/run_oss20_gen.log 2>&1
kill $S
$P poc/run_lean.py check results/x4/lean_oss20_test.jsonl > results/x4/run_oss20_check.log 2>&1
echo "S2_X4a (gpt-oss-20b miniF2F) done $(date)" >> results/queue_log.txt
