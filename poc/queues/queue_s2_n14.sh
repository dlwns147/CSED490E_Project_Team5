#!/bin/bash
# N14 (docs/prereg/PREREG_N14.md): adapt a verified source program to a problem with one more rule. Starts its servers on whichever of
# GPUs 0-3 the caller passes (default: 0 = Qwen3-32B-AWQ on 8043, 2 = Qwen3.6 on 8042). Sources: results/n14/src_<prefix>_<prob>_*.py
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
CX="--arms solver --n_inst 4 --temperature 0.7 --fmt_fix --api_doc --max_tokens 8192"
lane() { model=$1 port=$2 gpu=$3 pre=$4 tag=$5 extra=$6
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 n14_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  for sd in 1 2 3; do
    for pair in "tsp cvrp the TSP (one vehicle, no capacity)" "cvrp vrptw capacitated vehicle routing without time windows"; do
      set -- $pair; src=$1 dst=$2; shift 2; desc="$*"
      $P poc/run_co.py --model_tag S2_N14_${tag}_${dst}_good_s$sd $CX --probs $dst --seed $sd --adapt_from results/n14/src_${pre}_${src}_good.py \
        --adapt_note "solves a related problem ($desc)" > results/run_S2_N14_${tag}_${dst}_good_s$sd.log 2>&1 &
      [ -f results/n14/src_${pre}_${src}_bad.py ] && $P poc/run_co.py --model_tag S2_N14_${tag}_${dst}_bad_s$sd $CX --probs $dst --seed $sd \
        --adapt_from results/n14/src_${pre}_${src}_bad.py --adapt_note "solves a related problem ($desc)" > results/run_S2_N14_${tag}_${dst}_bad_s$sd.log 2>&1 &
      $P poc/run_co.py --model_tag S2_N14_${tag}_${dst}_unrel_s$sd $CX --probs $dst --seed $sd --adapt_from results/n14/src_${pre}_knapsack_good.py \
        --adapt_note "solves a different problem (0/1 knapsack)" > results/run_S2_N14_${tag}_${dst}_unrel_s$sd.log 2>&1 &
    done
  done; wait
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 ${G1:-0} S2_N10 q32b "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8042 ${G2:-2} S2_N10m3 q36 "--max-num-seqs 64 --language-model-only" &
wait
echo "S2_N14 runs done $(date)" >> results/queue_log.txt
