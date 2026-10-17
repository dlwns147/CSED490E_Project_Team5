#!/bin/bash
# N9 (repair at medium effort, gpt-oss-120b, 8043 GPU0) and H7 (Qwen3.6-35B-A3B, 8047 GPU2 / 8048 GPU3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
( S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8043 0 0.88 n9_o120) || exit 1
  POC_BASE_URL=http://127.0.0.1:8043/v1 POC_REASONING_EFFORT=medium REP_SUFFIX=_med $P poc/repair_cc.py oss120_low 1 --max_tokens 16000 > results/h2/run_rep_med_oss120_low_s1.log 2>&1
  kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8047 2 0.88 h7_q36a --max-num-seqs 64 --language-model-only) || exit 1
  for sd in 1 2 3; do POC_BASE_URL=http://127.0.0.1:8047/v1 $P poc/run_cc.py run q36_plain $sd --max_tokens 28000 > results/h2/run_full_q36_plain_s$sd.log 2>&1 & done; wait
  kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8048 3 0.88 h7_q36b --max-num-seqs 64 --language-model-only) || exit 1
  for arm in plain parserintrobust; do fl=""; [ $arm = parserintrobust ] && fl="--parser_int --snippet_robust"
    for sd in 1 2; do POC_BASE_URL=http://127.0.0.1:8048/v1 $P poc/run_solomon.py run q36_$arm $sd $fl --max_tokens 16000 > results/h3/run_q36_${arm}_s$sd.log 2>&1 & done; wait; done
  kill $S ) &
wait
echo "S2_N9H7 runs done $(date)" >> results/queue_log.txt
