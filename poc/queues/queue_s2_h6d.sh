#!/bin/bash
# H6d (PREREG_H6.md): Qwen3.8 no-think, code-only instruction, 28k cap, seed 1 (8046 GPU0).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.8-27B-FP8 8046 0 0.88 h6d_q38 --max-num-seqs 64 --language-model-only) || exit 1
POC_BASE_URL=http://127.0.0.1:8046/v1 $P poc/run_cc.py run q38_codeonly 1 --codeonly --max_tokens 28000 > results/h2/run_full_q38_codeonly_s1.log 2>&1
kill $S
echo "S2_H6d runs done $(date)" >> results/queue_log.txt
