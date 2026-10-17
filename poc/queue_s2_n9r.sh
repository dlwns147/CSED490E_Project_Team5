#!/bin/bash
# N9 replication (PREREG_N.md, positive claims need >= 3 seeds): medium-effort repair of the low-effort failures, seeds 2 and 3,
# gpt-oss-120b on 8043 (GPU 0) and 8042 (GPU 2).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
lane() { port=$1 gpu=$2 sd=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b $port $gpu 0.88 n9r_s$sd) || return 1
  POC_BASE_URL=http://127.0.0.1:$port/v1 POC_REASONING_EFFORT=medium REP_SUFFIX=_med $P poc/repair_cc.py oss120_low $sd --max_tokens 16000 > results/h2/run_rep_med_oss120_low_s$sd.log 2>&1
  kill $S; }
lane 8043 0 2 & lane 8042 2 3 & wait
echo "S2_N9R runs done $(date)" >> results/queue_log.txt
