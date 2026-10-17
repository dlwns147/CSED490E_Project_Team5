#!/bin/bash
# V3 (quality guard) + N6 (retrieved exemplars). 8046 Qwen3.8 (GPU0), 8042 gpt-oss-20b (GPU1), 8043 gpt-oss-120b (GPU3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
( POC_BASE_URL=http://127.0.0.1:8046/v1 V2_SUFFIX=_guard $P poc/reuse_repair.py q38_plain --guard > results/h3/run_v3_q38_plain.log 2>&1 ) &
( export POC_BASE_URL=http://127.0.0.1:8042/v1 POC_REASONING_EFFORT=low
  V2_SUFFIX=_guard $P poc/reuse_repair.py oss20_low_plain --guard --max_tokens 16000 > results/h3/run_v3_oss20_low_plain.log 2>&1 &
  $P poc/run_cc.py run oss20_low_ex_stmt 1 --exemplar stmt --max_tokens 16000 > results/h2/run_full_oss20_low_ex_stmt_s1.log 2>&1 &
  $P poc/run_cc.py run oss20_low_ex_draft 1 --exemplar draft:oss20_low --max_tokens 16000 > results/h2/run_full_oss20_low_ex_draft_s1.log 2>&1 & wait ) &
( export POC_BASE_URL=http://127.0.0.1:8043/v1 POC_REASONING_EFFORT=low
  $P poc/run_cc.py run oss120_low_ex_stmt 1 --exemplar stmt --max_tokens 16000 > results/h2/run_full_oss120_low_ex_stmt_s1.log 2>&1 &
  $P poc/run_cc.py run oss120_low_ex_draft 1 --exemplar draft:oss120_low --max_tokens 16000 > results/h2/run_full_oss120_low_ex_draft_s1.log 2>&1 & wait ) &
wait
echo "S2_V3N6 runs done $(date)" >> results/queue_log.txt
