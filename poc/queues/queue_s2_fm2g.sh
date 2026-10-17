#!/bin/bash
# FM2 model generality (PREREG_FM.md): gpt-oss-20b low on 8042 (GPU2): chain D sheet transfer, then self-mining chain I.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_REASONING_EFFORT=low POC_BASE_URL=http://127.0.0.1:8042/v1
for sd in 1 2; do $P poc/fact_mine.py test D verified $sd oss20_low --max_tokens 16000 > results/h3/run_fm_D_verified_on_oss20_s$sd.log 2>&1; done
$P poc/fact_mine.py mine I --v2 --max_tokens 16000 > results/h3/run_fm_mine_I.log 2>&1
for sd in 1 2; do $P poc/fact_mine.py test I verified $sd --max_tokens 16000 > results/h3/run_fm_I_verified_s$sd.log 2>&1; done
echo "S2_FM2g runs done $(date)" >> results/queue_log.txt
