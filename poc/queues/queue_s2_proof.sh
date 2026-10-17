#!/bin/bash
# PROOF phase 1 (docs/prereg/PREREG_PROOF.md): Goedel-Prover-V2-8B, DeepSeek-Prover-V2-7B, Qwen3-14B-AWQ thinking on miniF2F test, 8 attempts.
# Waits (<= 8 h) for the downloads and for a free GPU among 0-3 (claim results/.gpu_claim_<g>); Lean checks run on the CPU in the background.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 360); do [ -f /SSD/huggingface/deepseek-ai/DeepSeek-Prover-V2-7B/config.json ] && [ -f /SSD/huggingface/Goedel-LM/Goedel-Prover-V2-8B/config.json ] && break; sleep 20; done
G=""; for i in $(seq 1440); do for g in 3 0 1 2; do
  [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$g 2>/dev/null && { G=$g; break 2; }; done; sleep 20; done
[ -n "$G" ] || { echo "S2_PROOF: no free GPU within 8 h $(date)" >> results/queue_log.txt; exit 1; }
echo "S2_PROOF started on GPU$G $(date)" >> results/queue_log.txt
for spec in "/SSD/huggingface/Goedel-LM/Goedel-Prover-V2-8B gpv2" "/SSD/huggingface/deepseek-ai/DeepSeek-Prover-V2-7B dspv2" "/SSD/huggingface/Qwen/Qwen3-14B-AWQ q14a_think --think"; do
  set -- $spec; dir=$1 tag=$2 fl=$3
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir 8078 $G 0.88 proof_${tag}_$att) || { sleep 60; continue; }
    POC_BASE_URL=http://127.0.0.1:8078/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen $tag test 8 --max_tokens 16000 $fl >> results/x4/run_proof_$tag.log 2>&1
    kill $S; sleep 20
    [ "$(wc -l < results/x4/lean_${tag}_test.jsonl)" -ge 1952 ] && break
  done
  echo "S2_PROOF $tag generated $(wc -l < results/x4/lean_${tag}_test.jsonl)/1952 $(date)" >> results/queue_log.txt
  ( $P poc/run_lean.py check results/x4/lean_${tag}_test.jsonl >> results/x4/run_proof_$tag.log 2>&1
    echo "S2_PROOF $tag checked $(date)" >> results/queue_log.txt ) &
done
rmdir results/.gpu_claim_$G
wait
$P poc/analyze_proof.py > results/x4/proof_analysis.log 2>&1
echo "S2_PROOF analysis -> results/x4/proof_analysis.log $(date)" >> results/queue_log.txt
