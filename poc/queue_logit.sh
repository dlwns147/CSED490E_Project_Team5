#!/bin/bash
# Logit probe (teacher forcing, no sampling): log P(algorithm part | prompt) for monotone / Graham / collinear-pass hull programs under K=0, K=8, K=8 "may".
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
for spec in "Qwen3-8B:8b:8060" "Qwen3-14B:14b:8061" "Qwen3-32B-AWQ:32b:8062"; do
  IFS=: read mdl m port <<< "$spec"
  S=$(start /SSD/huggingface/Qwen/$mdl $port q${m}_logit); export POC_BASE_URL=http://127.0.0.1:$port/v1
  $P poc/logit_probe.py qwen3_$m > results/run_logit_probe_$m.log 2>&1
  kill $S; sleep 20
done
echo LOGIT_DONE >> results/queue_log.txt
