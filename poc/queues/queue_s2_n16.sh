#!/bin/bash
# N16 (docs/prereg/PREREG_N16.md): first programs with log-probs (no documentation) + snippet arm, seeds 1-3, three Qwen models.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 port=$2 gpu=$3 tag=$4 mt=$5 extra=$6
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 n16_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  C="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --max_tokens $mt"
  for sd in 1 2 3; do
    $P poc/run_co.py --model_tag S2_N16_${tag}_nodoclp_s$sd $C --seed $sd --logprobs > results/run_S2_N16_${tag}_nodoclp_s$sd.log 2>&1 &
    $P poc/run_co.py --model_tag S2_N16_${tag}_snippet_s$sd $C --seed $sd --api_doc --api_doc_task > results/run_S2_N16_${tag}_snippet_s$sd.log 2>&1 &
  done; wait
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 q32b 4096 "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 1 q36 8192 "--max-num-seqs 64 --language-model-only" &
lane /SSD/huggingface/Qwen/Qwen3-8B 8044 2 q8b 4096 "" &
wait
echo "S2_N16 runs done $(date)" >> results/queue_log.txt
