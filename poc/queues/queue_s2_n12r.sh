#!/bin/bash
# N12 replication arms (PREREG_N10.md): seeds 2-3 of no-helpers / thinking (geometry) and BM25 snippets / thinking (optimization),
# Qwen3-32B-AWQ; 8043 GPU 0 geometry, 8042 GPU 2 optimization. Tags as N10 (S2_N10_geo_none_s2, ...).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
M=/SSD/huggingface/Qwen/Qwen3-32B-AWQ
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix"
g() { tag=S2_N10_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $GX "$@" > results/run_$tag.log 2>&1; }
c() { tag=S2_N10_co_$1; shift; $P poc/run_co.py --model_tag $tag $CX "$@" > results/run_$tag.log 2>&1; }
( S=$(bash poc/start_server.sh $M 8043 0 0.88 n12r_geo) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8043/v1
  for sd in 2 3; do g none_s$sd --seed $sd --max_tokens 4096 & g think_s$sd --seed $sd --distract 8 --think --max_tokens 16000 & done; wait
  kill $S ) &
( S=$(bash poc/start_server.sh $M 8042 2 0.88 n12r_co) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8042/v1
  for sd in 2 3; do c rag3_s$sd --seed $sd --retrieve 3 --max_tokens 4096 & c think_s$sd --seed $sd --api_doc --think --max_tokens 16000 & done; wait
  kill $S ) &
wait
echo "S2_N12R runs done $(date)" >> results/queue_log.txt
