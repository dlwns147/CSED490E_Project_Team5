#!/bin/bash
# H2e (PREREG_H2C.md): gpt-oss-120b high, 64k cap, seed 1, problems sharded over 3 servers (GPUs 0-2); shards merged at the end.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=high
run() { gpu=$1 port=$2 i=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b $port $gpu 0.90 h2e_o120_$i --max-model-len 65536) || return
  POC_BASE_URL=http://127.0.0.1:$port/v1 CC_SHARD=$i/3 $P poc/run_cc.py run oss120_high64k 1 --max_tokens 62000 > results/h2/run_full_oss120_high64k_s1_shard$i.log 2>&1
  kill $S; }
run 0 8043 0 & run 1 8044 1 & run 2 8045 2 &
wait
cat results/h2/cc_full_oss120_high64k_s1_shard0of3.jsonl results/h2/cc_full_oss120_high64k_s1_shard1of3.jsonl results/h2/cc_full_oss120_high64k_s1_shard2of3.jsonl > results/h2/cc_full_oss120_high64k_s1.jsonl
echo "S2_H2e runs done $(date)" >> results/queue_log.txt
