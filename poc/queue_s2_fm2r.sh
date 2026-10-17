#!/bin/bash
# FM2 replication (PREREG_FM.md): chains E, F on 8043 and G, H on 8044 (gpt-oss-120b low); verified sheets tested on the 48 test instances.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low
lane() { port=$1; shift; ( export POC_BASE_URL=http://127.0.0.1:$port/v1
  for c in "$@"; do $P poc/fact_mine.py mine $c --v2 --max_tokens 16000 > results/h3/run_fm_mine_$c.log 2>&1
    for sd in 1 2; do $P poc/fact_mine.py test $c verified $sd --max_tokens 16000 > results/h3/run_fm_${c}_verified_s$sd.log 2>&1; done; done ); }
lane 8043 E F & lane 8044 G H &
wait
echo "S2_FM2r runs done $(date)" >> results/queue_log.txt
