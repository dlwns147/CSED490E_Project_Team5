#!/bin/bash
# Phase 4b: Qwen3.6 (no thinking) on the 50 inequality statements with the inequality toolkit fact sheet; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_2 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8093 2 0.88 proof_ineq_$att --max-num-seqs 64 --language-model-only) || { sleep 60; continue; }
  LEAN_HINT=results/x4/ineq_toolkit.txt LEAN_ONLY=results/x4/ineq50.txt POC_BASE_URL=http://127.0.0.1:8093/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen q36_ineqhint test 8 >> results/x4/run_proof_ineq.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/x4/lean_q36_ineqhint_test.jsonl)" -ge 400 ] && break
done
rmdir results/.gpu_claim_2
$P poc/run_lean.py check results/x4/lean_q36_ineqhint_test.jsonl >> results/x4/run_proof_ineq.log 2>&1
echo "S2_PROOF10 (inequality toolkit, Qwen3.6) generated + checked $(date)" >> results/queue_log.txt
