#!/bin/bash
# FM (docs/prereg/PREREG_FM.md): two mining chains on gpt-oss-120b low (A: 8043 GPU3, B: 8044 GPU1), test on the 48 held-out instances;
# per-instance repair baseline on 8044; transfer of chain A's sheet to gpt-oss-20b low (8042 GPU2).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low
( export POC_BASE_URL=http://127.0.0.1:8043/v1
  $P poc/fact_mine.py mine A --max_tokens 16000 > results/h3/run_fm_mine_A.log 2>&1
  for w in verified unverified; do for sd in 1 2; do $P poc/fact_mine.py test A $w $sd --max_tokens 16000 > results/h3/run_fm_A_${w}_s$sd.log 2>&1; done; done ) &
( export POC_BASE_URL=http://127.0.0.1:8044/v1
  $P poc/fact_mine.py mine B --max_tokens 16000 > results/h3/run_fm_mine_B.log 2>&1
  for w in verified unverified; do for sd in 1 2; do $P poc/fact_mine.py test B $w $sd --max_tokens 16000 > results/h3/run_fm_B_${w}_s$sd.log 2>&1; done; done
  for sd in 1 2; do $P poc/run_solomon.py repair oss120_low_plain $sd --max_tokens 16000 > results/h3/run_rep_oss120_low_plain_s$sd.log 2>&1; done ) &
( export POC_BASE_URL=http://127.0.0.1:8042/v1
  while [ ! -s results/h3/fm_chain_A.json ]; do sleep 60; done
  for sd in 1 2; do $P poc/fact_mine.py test A verified $sd oss20_low --max_tokens 16000 > results/h3/run_fm_A_verified_on_oss20_s$sd.log 2>&1; done ) &
wait
echo "S2_FM runs done $(date)" >> results/queue_log.txt
