#!/bin/bash
# PROOF-P7: DeepSeek-Prover-V2-7B, samples 9-32 on its 79 statements unsolved after 8 (results/x4/dspv2_unsolved8.txt); GPU1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_1 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/deepseek-ai/DeepSeek-Prover-V2-7B 8088 1 0.88 proof_dspv2k32_$att --max-model-len 40000) || { sleep 60; continue; }
  LEAN_ONLY=results/x4/dspv2_unsolved8.txt POC_BASE_URL=http://127.0.0.1:8088/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen dspv2 test 32 --max_tokens 32000 --think --card_prompt >> results/x4/run_proof_dspv2.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/x4/lean_dspv2_test.jsonl)" -ge 3848 ] && break
done
rmdir results/.gpu_claim_1
$P poc/run_lean.py check results/x4/lean_dspv2_test.jsonl >> results/x4/run_proof_dspv2.log 2>&1
echo "S2_PROOF dspv2 k=32 on the unsolved tail done ($(wc -l < results/x4/lean_dspv2_test.jsonl) rows, checked) $(date)" >> results/queue_log.txt
