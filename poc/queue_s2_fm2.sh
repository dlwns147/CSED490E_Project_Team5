#!/bin/bash
# FM2 (results/PREREG_FM.md, FM2 section): chains C (8043) and D (8044) on gpt-oss-120b low; test verified + unverified sheets.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low
ch() { port=$1 c=$2; ( export POC_BASE_URL=http://127.0.0.1:$port/v1
  $P poc/fact_mine.py mine $c --v2 --max_tokens 16000 > results/h3/run_fm_mine_$c.log 2>&1
  for w in verified unverified; do for sd in 1 2; do $P poc/fact_mine.py test $c $w $sd --max_tokens 16000 > results/h3/run_fm_${c}_${w}_s$sd.log 2>&1; done; done ); }
ch 8043 C & ch 8044 D &
wait
echo "S2_FM2 runs done $(date)" >> results/queue_log.txt
