#!/bin/bash
# X6-AUTO (docs/prereg/PREREG_X3.md): introspected API card instead of the hand-written snippet; Qwen3-32B GPU0, Qwen3-8B GPU3, Qwen3.6 GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { g=$1 dir=$2 tag=$3 port=$4 tmt=$5 extra=$6
  mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $g 0.88 x6auto_${tag}_$att $extra) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=14400
    for sd in 1 2 3; do
      $P poc/run_nlopt.py $tag mipa $sd --max_tokens 8192 >> results/x3/run_${tag}_mipa_s$sd.log 2>&1 &
      $P poc/run_nlopt.py $tag thinka $sd --think --max_tokens $tmt >> results/x3/run_${tag}_thinka_s$sd.log 2>&1 &
    done; wait
    kill $S; sleep 20
    n=$(cat results/x3/opt_${tag}_mipa_s*.jsonl results/x3/opt_${tag}_thinka_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 2070 ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_X6AUTO $tag done ($n/2070) $(date)" >> results/queue_log.txt; }
lane 0 /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b 8094 16000 "" &
lane 3 /SSD/huggingface/Qwen/Qwen3-8B q8b 8095 16000 "" &
( export POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20
  lane 2 /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 q36d 8096 80000 "--max-num-seqs 64 --language-model-only --max-model-len 90000" ) &
wait
echo "S2_X6AUTO runs done $(date)" >> results/queue_log.txt
