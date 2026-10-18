#!/bin/bash
# PROOF phase 2: gpt-oss-20b low with a verified proof of the most similar other statement (Goedel's) in the prompt; GPU0.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_0 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8089 0 0.88 proof_oss20ex_$att) || { sleep 60; continue; }
  POC_REASONING_EFFORT=low POC_BASE_URL=http://127.0.0.1:8089/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen oss20_ex test 8 --exemplar gpv2 >> results/x4/run_proof_oss20_ex.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/x4/lean_oss20_ex_test.jsonl)" -ge 1952 ] && break
done
rmdir results/.gpu_claim_0
$P poc/run_lean.py check results/x4/lean_oss20_ex_test.jsonl >> results/x4/run_proof_oss20_ex.log 2>&1
echo "S2_PROOF oss20_ex (phase 2) generated + checked $(date)" >> results/queue_log.txt
$P poc/analyze_proof.py oss20 oss20_ex >> results/x4/run_proof_oss20_ex.log 2>&1
