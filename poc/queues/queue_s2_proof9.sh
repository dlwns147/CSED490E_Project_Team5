#!/bin/bash
# PROOF-R: DeepSeek-Prover-V2-7B revises its failed first attempts from Lean's error lines; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_2 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/deepseek-ai/DeepSeek-Prover-V2-7B 8091 2 0.88 proof_revise_dsp_$att --max-model-len 40000) || { sleep 60; continue; }
  POC_BASE_URL=http://127.0.0.1:8091/v1 POC_TIMEOUT=7200 $P poc/run_lean.py revise dspv2 test >> results/x4/run_revise_dspv2.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/x4/revise_dspv2_test.jsonl)" -ge 112 ] && break
done
rmdir results/.gpu_claim_2
echo "S2_PROOF9 (DeepSeek-Prover revision from compiler errors) done $(wc -l < results/x4/revise_dspv2_test.jsonl) rows $(date)" >> results/queue_log.txt
