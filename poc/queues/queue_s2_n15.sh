#!/bin/bash
# N15 (docs/prereg/PREREG_N15.md): solver-library choice. Qwen3-32B 8043 GPU0, gpt-oss-20b low 8044 GPU1, Qwen3.6 8045 GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 port=$2 gpu=$3 tag=$4 mt=$5 eff=$6 extra=$7
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 n15_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  C="--n_inst 4 --temperature 0.7 --fmt_fix --max_tokens $mt"
  ALL=knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw
  for sd in 1 2; do
    for L in free cpsat mip; do $P poc/run_co.py --model_tag S2_N15_${tag}_${L}_s$sd --arms solver --probs $ALL --lib $L --seed $sd $C > results/run_S2_N15_${tag}_${L}_s$sd.log 2>&1 & done
    $P poc/run_co.py --model_tag S2_N15_${tag}_routing_s$sd --arms solver --probs tsp,cvrp,vrptw --lib routing --seed $sd $C > results/run_S2_N15_${tag}_routing_s$sd.log 2>&1 &
    $P poc/run_co.py --model_tag S2_N15_${tag}_none_s$sd --arms heuristic --probs $ALL --seed $sd $C > results/run_S2_N15_${tag}_none_s$sd.log 2>&1 &
    [ $sd = 2 ] && $P poc/run_co.py --model_tag S2_N15_${tag}_default_s2 --arms solver --probs $ALL --seed 2 $C > results/run_S2_N15_${tag}_default_s2.log 2>&1 &
    wait
  done
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 q32b 4096 "" "" &
lane /SSD/huggingface/openai/gpt-oss-20b 8044 1 oss20 16000 low "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 2 q36 8192 "" "--max-num-seqs 64 --language-model-only" &
wait
echo "S2_N15 runs done $(date)" >> results/queue_log.txt
