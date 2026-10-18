#!/bin/bash
# PROOF-P6: Goedel-Prover-V2-8B, samples 9-32 on the 64 statements unsolved after 8 attempts (results/x4/gpv2_unsolved8.txt); GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_3 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Goedel-LM/Goedel-Prover-V2-8B 8083 3 0.88 proof_gpv2k32_$att --max-model-len 40000) || { sleep 60; continue; }
  LEAN_ONLY=results/x4/gpv2_unsolved8.txt POC_BASE_URL=http://127.0.0.1:8083/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen gpv2 test 32 --max_tokens 32000 --think --card_prompt >> results/x4/run_proof_gpv2.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/x4/lean_gpv2_test.jsonl)" -ge 3488 ] && break
done
rmdir results/.gpu_claim_3
$P poc/run_lean.py check results/x4/lean_gpv2_test.jsonl >> results/x4/run_proof_gpv2.log 2>&1
echo "S2_PROOF gpv2 k=32 on the unsolved tail done ($(wc -l < results/x4/lean_gpv2_test.jsonl) rows, checked) $(date)" >> results/queue_log.txt
