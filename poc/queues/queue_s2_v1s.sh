#!/bin/bash
# V1s (PREREG_V.md): 48 more mining-instance candidates for gpt-oss-20b low plain (8042) and + docs (8043 serves 120b, so both on 8042).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low POC_BASE_URL=http://127.0.0.1:8042/v1 SOLOMON_ONLY=c101,c201,r101,r201,rc101,rc201,r105,rc105
for sd in 3 4 5 6 7 8; do
  $P poc/run_solomon.py run oss20_low_plain $sd --max_tokens 16000 > results/h3/run_oss20_low_plain_s$sd.log 2>&1 &
  $P poc/run_solomon.py run oss20_low_docs $sd --snippet --max_tokens 16000 > results/h3/run_oss20_low_docs_s$sd.log 2>&1 &
  wait
done
unset SOLOMON_ONLY
REUSE_SEEDS=1,2,3,4,5,6,7,8 REUSE_SUFFIX=_v1s $P poc/analyze_reuse.py oss20_low_plain oss20_low_docs > results/h3/reuse_v1s.log 2>&1
echo "S2_V1s runs done $(date)" >> results/queue_log.txt
