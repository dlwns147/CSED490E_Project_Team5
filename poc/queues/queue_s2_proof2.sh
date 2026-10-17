#!/bin/bash
# PROOF phase 1, parallel lanes (docs/prereg/PREREG_PROOF.md). Replaces the sequential queue_s2_proof.sh at 21:4x:
#  lane A: the running Goedel-Prover-V2 generation (PID 2527596, server PID 2475715, GPU3) -> stop its server, check, free the claim;
#  lanes B / C: DeepSeek-Prover-V2-7B and Qwen3-14B-AWQ thinking, each on the first free GPU among 0-3 (claim results/.gpu_claim_<g>).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
claim() { for i in $(seq 1440); do for g in 1 3 0 2; do
    [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$g 2>/dev/null && { echo $g; return 0; }
  done; sleep 20; done; return 1; }
check() { $P poc/run_lean.py check results/x4/lean_$1_test.jsonl >> results/x4/run_proof_$1.log 2>&1; echo "S2_PROOF $1 checked $(date)" >> results/queue_log.txt; }
laneA() { for i in $(seq 1440); do ps -p 2527596 >/dev/null || break; sleep 20; done
  kill 2475715; sleep 20; rmdir results/.gpu_claim_3
  if [ "$(wc -l < results/x4/lean_gpv2_test.jsonl)" -lt 1952 ]; then   # generation died early: finish it on a fresh server
    G=$(claim) || return 1
    S=$(bash poc/start_server.sh /SSD/huggingface/Goedel-LM/Goedel-Prover-V2-8B 8078 $G 0.88 proof_gpv2_b --max-model-len 40000) && {
      POC_BASE_URL=http://127.0.0.1:8078/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen gpv2 test 8 --max_tokens 32000 --think --card_prompt >> results/x4/run_proof_gpv2.log 2>&1
      kill $S; sleep 20; }; rmdir results/.gpu_claim_$G; fi
  echo "S2_PROOF gpv2 generated $(wc -l < results/x4/lean_gpv2_test.jsonl)/1952 $(date)" >> results/queue_log.txt; check gpv2; }
lane() { dir=$1 tag=$2 port=$3 mt=$4; shift 4
  G=$(claim) || { echo "S2_PROOF $tag: no free GPU $(date)" >> results/queue_log.txt; return 1; }
  echo "S2_PROOF $tag started on GPU$G $(date)" >> results/queue_log.txt
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $G 0.88 proof_${tag}_$att --max-model-len 40000) || { sleep 60; continue; }
    POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=7200 $P poc/run_lean.py gen $tag test 8 --max_tokens $mt "$@" >> results/x4/run_proof_$tag.log 2>&1
    kill $S; sleep 20
    [ "$(wc -l < results/x4/lean_${tag}_test.jsonl)" -ge 1952 ] && break
  done
  rmdir results/.gpu_claim_$G
  echo "S2_PROOF $tag generated $(wc -l < results/x4/lean_${tag}_test.jsonl)/1952 $(date)" >> results/queue_log.txt; check $tag; }
laneA &
lane /SSD/huggingface/deepseek-ai/DeepSeek-Prover-V2-7B dspv2 8079 32000 --think --card_prompt &
lane /SSD/huggingface/Qwen/Qwen3-14B-AWQ q14a_think 8080 16000 --think &
wait
$P poc/analyze_proof.py > results/x4/proof_analysis.log 2>&1
echo "S2_PROOF analysis -> results/x4/proof_analysis.log $(date)" >> results/queue_log.txt
