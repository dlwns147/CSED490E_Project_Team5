#!/bin/bash
# U1 (results/PREREG_U1.md): base samples with log-probs + three cures, geometry + optimization suites, three Qwen models.
# Starts after X2 (bounded wait). Tags S2_U1_<model>_{geo,co}_<arm>_s<seed>.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
# 22:29: started directly on GPUs 0, 2, 3 (GPU1 still holds the last X1 thinking requests)
echo "S2_U1 q8b lane started (port 8056, GPU3) $(date)" >> results/queue_log.txt
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix"
lane() { model=$1 port=$2 gpu=$3 tag=$4 tmt=$5 extra=$6
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 u1_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  g() { t=S2_U1_${tag}_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $t $GX "$@" > results/run_$t.log 2>&1; }
  c() { t=S2_U1_${tag}_co_$1; shift; $P poc/run_co.py --model_tag $t $CX "$@" > results/run_$t.log 2>&1; }
  for sd in 1 2 3; do g base_s$sd --seed $sd --distract 8 --logprobs --max_tokens 4096 & c base_s$sd --seed $sd --api_doc --logprobs --max_tokens 4096 & done
  g fact_s1 --seed 1 --distract 0 --algo_hint --max_tokens 4096 & g decor_s1 --seed 1 --max_tokens 4096 &
  c fact_s1 --seed 1 --api_doc --api_doc_task --max_tokens 4096 & c decor_s1 --seed 1 --retrieve 3 --max_tokens 4096 & wait
  g think_s1 --seed 1 --distract 8 --think --max_tokens $tmt & c think_s1 --seed 1 --api_doc --think --max_tokens $tmt & wait
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-8B 8056 3 q8b 16000 ""
echo "S2_U1 q8b lane done $(date)" >> results/queue_log.txt
