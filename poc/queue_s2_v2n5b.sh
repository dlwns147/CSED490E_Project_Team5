#!/bin/bash
# V2 re-run + N5b + H6b. 8046 Qwen3.8 (GPU0), 8049 Qwen3.8 (GPU2), 8042 gpt-oss-20b (GPU1), 8043 gpt-oss-120b (GPU3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
( POC_BASE_URL=http://127.0.0.1:8046/v1 V2_SUFFIX=_fb $P poc/reuse_repair.py q38_plain > results/h3/run_v2_q38_plain_fb.log 2>&1
  POC_BASE_URL=http://127.0.0.1:8046/v1 POC_TEMPLATE_EFFORT=medium $P poc/run_cc.py run q38_thinkmed 1 --think > results/h2/run_full_q38_thinkmed_s1.log 2>&1 ) &
( POC_BASE_URL=http://127.0.0.1:8049/v1 POC_TEMPLATE_EFFORT=low $P poc/run_cc.py run q38_thinklow 1 --think > results/h2/run_full_q38_thinklow_s1.log 2>&1 ) &
( export POC_BASE_URL=http://127.0.0.1:8042/v1 POC_REASONING_EFFORT=low
  $P poc/reuse_repair.py oss20_low_plain --max_tokens 16000 > results/h3/run_v2_oss20_low_plain.log 2>&1
  $P poc/oracle_cc.py all oss20_low 1 --max_tokens 16000 > results/h2/run_n5_oss20_low_s1.log 2>&1 ) &
( export POC_BASE_URL=http://127.0.0.1:8043/v1 POC_REASONING_EFFORT=low
  $P poc/reuse_repair.py oss120_low_plain --max_tokens 16000 > results/h3/run_v2_oss120_low_plain.log 2>&1
  $P poc/oracle_cc.py all oss120_low 1 --max_tokens 16000 > results/h2/run_n5_oss120_low_s1.log 2>&1 ) &
wait
echo "S2_V2N5b runs done $(date)" >> results/queue_log.txt
