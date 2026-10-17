#!/bin/bash
# X4 replication of the log-prob half on a second Qwen model: Qwen3.6 no-think, miniF2F test, k = 8, raw log-probs; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8055 2 0.88 x4d_q36 --max-num-seqs 64 --language-model-only) || exit 1
POC_BASE_URL=http://127.0.0.1:8055/v1 $P poc/run_lean.py gen q36 test 8 --logprobs --max_tokens 8192 > results/x4/run_q36_gen.log 2>&1
kill $S
$P poc/run_lean.py check results/x4/lean_q36_test.jsonl > results/x4/run_q36_check.log 2>&1
$P poc/analyze_x4_lp.py q36 > results/x4/lp_q36.log 2>&1
echo "S2_X4d (Qwen3.6 miniF2F with log-probs) done $(date)" >> results/queue_log.txt
