#!/bin/bash
# H2e replication: gpt-oss-120b high, 64k cap, seeds 2 (GPUs 0-1) and 3 (GPUs 2-3), each sharded over 2 servers.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=high
run() { gpu=$1 port=$2 sd=$3 i=$4
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b $port $gpu 0.90 h2er_o120_${sd}_$i --max-model-len 65536) || return
  POC_BASE_URL=http://127.0.0.1:$port/v1 CC_SHARD=$i/2 $P poc/run_cc.py run oss120_high64k $sd --max_tokens 62000 > results/h2/run_full_oss120_high64k_s${sd}_shard$i.log 2>&1
  kill $S; }
run 0 8043 2 0 & run 1 8044 2 1 & run 2 8045 3 0 & run 3 8046 3 1 &
wait
for sd in 2 3; do cat results/h2/cc_full_oss120_high64k_s${sd}_shard0of2.jsonl results/h2/cc_full_oss120_high64k_s${sd}_shard1of2.jsonl > results/h2/cc_full_oss120_high64k_s$sd.jsonl; done
echo "S2_H2e replication done $(date)" >> results/queue_log.txt
