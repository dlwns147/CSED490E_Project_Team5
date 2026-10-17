#!/bin/bash
# X3 (results/PREREG_X3.md): starts when X2 has finished (bounded wait); GPU0 Qwen3-32B no-think, GPU2 gpt-oss-20b, GPU3 Qwen3-32B think
# (GPU3 only after X1 is done).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 720); do grep -q "S2_X2 runs done" results/queue_log.txt && break; sleep 20; done
grep -q "S2_X2 runs done" results/queue_log.txt || { echo "X3 waiter gave up $(date)" >> results/queue_log.txt; exit 1; }
echo "S2_X3 started $(date)" >> results/queue_log.txt
o() { $P poc/run_nlopt.py "$@" > results/x3/run_$1_$2_s$3.log 2>&1; }
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8050 0 0.88 x3_q32b) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8050/v1
  for sd in 1 2 3; do o q32b mip $sd & o q32b mipf $sd & o q32b cpsat $sd & o q32b text $sd & done; wait
  for sd in 1 2 3; do o q32b think $sd --think --max_tokens 16000 & done; wait; kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8051 2 0.88 x3_oss20) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8051/v1
  for sd in 1 2 3; do for md in mip mipf cpsat text; do POC_REASONING_EFFORT=low o oss20 $md $sd --max_tokens 16000 & done; done
  for sd in 1 2 3; do POC_REASONING_EFFORT=medium o oss20 think $sd --max_tokens 16000 & done; wait; kill $S ) &
wait
echo "S2_X3 runs done $(date)" >> results/queue_log.txt
