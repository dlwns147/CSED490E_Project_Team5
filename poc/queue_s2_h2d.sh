#!/bin/bash
# H2d (PREREG_H2C.md): gpt-oss-120b high effort on the 311 contest problems, 3 seeds on 3 servers (GPUs 0-2).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=high
run() { gpu=$1 port=$2 sd=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b $port $gpu 0.88 h2d_o120_$sd) || return
  POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run oss120_high $sd --max_tokens 30000 > results/h2/run_full_oss120_high_s$sd.log 2>&1
  kill $S; }
run 0 8043 1 & run 1 8044 2 & run 2 8045 3 &
wait
echo "S2_H2d runs done $(date)" >> results/queue_log.txt
