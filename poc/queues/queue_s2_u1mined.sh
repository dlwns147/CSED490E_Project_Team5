#!/bin/bash
# U1-MINED (docs/prereg/PREREG_U1.md): optimization suite, mined program of another problem type as the fact, cure seeds 1-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --resume"
lane() { g=$1 dir=$2 tag=$3 port=$4 extra=$5
  mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $g 0.88 u1mined_${tag}_$att $extra) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1
    for sd in 1 2 3; do t=S2_U1_${tag}_co_mined_s$sd
      $P poc/run_co.py --model_tag $t $CX --seed $sd --mined_from S2_U1_${tag}_co_base --max_tokens 4096 >> results/run_$t.log 2>&1 & done; wait
    kill $S; sleep 20
    n=$(cat results/co_S2_U1_${tag}_co_mined_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 300 ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_U1MINED $tag done ($n/300) $(date)" >> results/queue_log.txt; }
lane 1 /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b 8104 "" &
lane 2 /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 q36 8105 "--max-num-seqs 64 --language-model-only" &
wait
lane 1 /SSD/huggingface/Qwen/Qwen3-8B q8b 8106 ""
