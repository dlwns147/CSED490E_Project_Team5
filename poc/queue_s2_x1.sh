#!/bin/bash
# X1 (results/PREREG_X1.md): short-answer competition math. GPU0 Qwen3-32B no-think text+prog, GPU1 Qwen3-32B thinking,
# GPU2 gpt-oss-20b low text+prog + medium text, GPU3 Qwen3.6 text+prog+thinking. Seeds 1-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
m() { $P poc/run_math.py "$@" > results/x1/run_$1_$2_s$3.log 2>&1; }
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 0.88 x1_q32b) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8043/v1
  for sd in 1 2 3; do m q32b text $sd --max_tokens 8192 & m q32b prog $sd --max_tokens 8192 & done; wait; kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8044 1 0.88 x1_q32b_think) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8044/v1
  for sd in 1 2 3; do m q32b think $sd --think --max_tokens 28000 & done; wait; kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8045 2 0.88 x1_oss20) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8045/v1
  for sd in 1 2 3; do
    POC_REASONING_EFFORT=low m oss20 text $sd --max_tokens 16000 & POC_REASONING_EFFORT=low m oss20 prog $sd --max_tokens 16000 &
    POC_REASONING_EFFORT=medium m oss20 think $sd --max_tokens 16000 &
  done; wait; kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8046 3 0.88 x1_q36 --max-num-seqs 64 --language-model-only) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8046/v1
  for sd in 1 2 3; do m q36 text $sd --max_tokens 8192 & m q36 prog $sd --max_tokens 8192 & m q36 think $sd --think --max_tokens 28000 & done; wait; kill $S ) &
wait
echo "S2_X1 runs done $(date)" >> results/queue_log.txt
