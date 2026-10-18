#!/bin/bash
# PROOF-R: Goedel-Prover-V2-8B revises its failed first attempts from Lean's error lines; GPU0.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_0 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Goedel-LM/Goedel-Prover-V2-8B 8090 0 0.88 proof_revise_$att --max-model-len 40000) || { sleep 60; continue; }
  POC_BASE_URL=http://127.0.0.1:8090/v1 POC_TIMEOUT=7200 $P poc/run_lean.py revise gpv2 test >> results/x4/run_revise_gpv2.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/x4/revise_gpv2_test.jsonl)" -ge 107 ] && break
done
rmdir results/.gpu_claim_0
echo "S2_PROOF8 (Goedel revision from compiler errors) done $(wc -l < results/x4/revise_gpv2_test.jsonl) rows $(date)" >> results/queue_log.txt
