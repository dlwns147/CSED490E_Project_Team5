#!/bin/bash
# N14b (PREREG_N14.md): adapt + the new rule's exact snippet vs snippet alone. Qwen3-32B 8043 GPU0, Qwen3.6 8042 GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
CX="--arms solver --n_inst 4 --temperature 0.7 --fmt_fix --api_doc --api_doc_task --max_tokens 8192"
lane() { model=$1 port=$2 gpu=$3 pre=$4 tag=$5 extra=$6
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 n14b_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  for sd in 1 2 3; do
    $P poc/run_co.py --model_tag S2_N14b_${tag}_cvrp_adsnip_s$sd $CX --probs cvrp --seed $sd --adapt_from results/n14/src_${pre}_tsp_good.py \
      --adapt_note "solves a related problem (the TSP (one vehicle, no capacity))" > results/run_S2_N14b_${tag}_cvrp_adsnip_s$sd.log 2>&1 &
    $P poc/run_co.py --model_tag S2_N14b_${tag}_vrptw_adsnip_s$sd $CX --probs vrptw --seed $sd --adapt_from results/n14/src_${pre}_cvrp_good.py \
      --adapt_note "solves a related problem (capacitated vehicle routing without time windows)" > results/run_S2_N14b_${tag}_vrptw_adsnip_s$sd.log 2>&1 &
    [ $sd -gt 1 ] && $P poc/run_co.py --model_tag S2_N14b_${tag}_snip_s$sd $CX --probs cvrp,vrptw --seed $sd > results/run_S2_N14b_${tag}_snip_s$sd.log 2>&1 &
  done; wait
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 S2_N10 q32b "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8042 2 S2_N10m3 q36 "--max-num-seqs 64 --language-model-only" &
wait
echo "S2_N14b runs done $(date)" >> results/queue_log.txt
