#!/bin/bash
# Re-run of the thinking arms lost when all four vLLM servers died at 2026-10-16 23:51:25 (NCCL watchdog termination in every engine at
# once): U1 think arms (GPU0 Qwen3-32B, GPU2 Qwen3.6, GPU3 Qwen3-8B) and X1 Qwen3-32B thinking (GPU1, 3 seeds, resumable).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix"
u1() { model=$1 port=$2 gpu=$3 tag=$4 tmt=$5 extra=$6
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 rr_u1_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  $P poc/run_geo_cross.py --model_tag S2_U1_${tag}_geo_think_s1 $GX --seed 1 --distract 8 --think --max_tokens $tmt > results/run_S2_U1_${tag}_geo_think_s1.log 2>&1 &
  $P poc/run_co.py --model_tag S2_U1_${tag}_co_think_s1 $CX --seed 1 --api_doc --think --max_tokens $tmt > results/run_S2_U1_${tag}_co_think_s1.log 2>&1 &
  wait; kill $S; echo "S2_U1 think re-run $tag done $(date)" >> results/queue_log.txt; }
x1() { S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8061 1 0.88 rr_x1_q32b) || return 1
  export POC_BASE_URL=http://127.0.0.1:8061/v1
  for sd in 1 2 3; do $P poc/run_math.py q32b think $sd --think --max_tokens 28000 > results/x1/run_q32b_think_s$sd.log 2>&1 & done; wait
  kill $S; echo "S2_X1 q32b thinking re-run done $(date)" >> results/queue_log.txt; }
u1 /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8058 0 q32b 16000 "" &
u1 /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8059 2 q36 28000 "--max-num-seqs 64 --language-model-only" &
u1 /SSD/huggingface/Qwen/Qwen3-8B 8060 3 q8b 16000 "" &
x1 &
wait
