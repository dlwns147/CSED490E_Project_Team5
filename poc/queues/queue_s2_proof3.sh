#!/bin/bash
# PROOF phase-1 addendum (docs/prereg/PREREG_PROOF.md): Qwen3.6 thinking (GPU0) and gpt-oss-20b medium (GPU1) on miniF2F test, 8 attempts.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { g=$1 dir=$2 tag=$3 port=$4 mt=$5 mml=$6; shift 6
  mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $g 0.88 proof_${tag}_$att --max-model-len $mml $SERVE_EXTRA) || { sleep 60; continue; }
    POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=14400 $P poc/run_lean.py gen $tag test 8 --max_tokens $mt "$@" >> results/x4/run_proof_$tag.log 2>&1
    kill $S; sleep 20
    [ "$(wc -l < results/x4/lean_${tag}_test.jsonl)" -ge 1952 ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_PROOF $tag generated $(wc -l < results/x4/lean_${tag}_test.jsonl)/1952 $(date)" >> results/queue_log.txt
  $P poc/run_lean.py check results/x4/lean_${tag}_test.jsonl >> results/x4/run_proof_$tag.log 2>&1
  echo "S2_PROOF $tag checked $(date)" >> results/queue_log.txt; }
( export POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20 SERVE_EXTRA="--max-num-seqs 64 --language-model-only"
  lane 0 /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 q36_think 8081 48000 52000 --think ) &
( export POC_REASONING_EFFORT=medium SERVE_EXTRA=""
  lane 1 /SSD/huggingface/openai/gpt-oss-20b oss20_medium 8082 32000 36000 ) &
wait
$P poc/analyze_proof.py > results/x4/proof_analysis.log 2>&1
echo "S2_PROOF3 analysis -> results/x4/proof_analysis.log $(date)" >> results/queue_log.txt
