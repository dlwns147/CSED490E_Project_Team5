#!/bin/bash
# N10 (docs/prereg/PREREG_N10.md): the fix-menu factorial for the router study. Qwen3-32B-AWQ no-think, T=0.7.
# Geometry lane: 8041 on GPU 1. Optimization lane: 8045 on GPU 3. Tags S2_N10_geo_<arm> / S2_N10_co_<arm>.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
M=/SSD/huggingface/Qwen/Qwen3-32B-AWQ
GT="hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks $GT"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix"
g() { tag=S2_N10_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $GX "$@" > results/run_$tag.log 2>&1; }
c() { tag=S2_N10_co_$1; shift; $P poc/run_co.py --model_tag $tag $CX "$@" > results/run_$tag.log 2>&1; }
( S=$(bash poc/start_server.sh $M 8041 1 0.88 n10_geo) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8041/v1
  g k8_s1 --seed 1 --distract 8 --max_tokens 4096 & g k8_s2 --seed 2 --distract 8 --max_tokens 4096 &
  g k8_s3 --seed 3 --distract 8 --max_tokens 4096 & g none_s1 --seed 1 --max_tokens 4096 &
  g auto_s1 --seed 1 --distract 8 --autoscope --max_tokens 4096 & wait
  g stdin_s1 --seed 1 --distract 8 --show_stdin --max_tokens 4096 & g plan_s1 --seed 1 --distract 8 --self_hint --max_tokens 4096 &
  g k0_s1 --seed 1 --distract 0 --max_tokens 4096 & g think_s1 --seed 1 --distract 8 --think --max_tokens 16000 & wait
  kill $S ) &
( S=$(bash poc/start_server.sh $M 8045 3 0.88 n10_co) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8045/v1
  c doc_s1 --seed 1 --api_doc --max_tokens 4096 & c doc_s2 --seed 2 --api_doc --max_tokens 4096 &
  c doc_s3 --seed 3 --api_doc --max_tokens 4096 & c nodoc_s1 --seed 1 --max_tokens 4096 &
  c rag3_s1 --seed 1 --retrieve 3 --max_tokens 4096 & wait
  c stdin_s1 --seed 1 --api_doc --show_stdin --max_tokens 4096 & c repair_s1 --seed 1 --api_doc --repair 1 --max_tokens 4096 &
  c snippet_s1 --seed 1 --api_doc --api_doc_task --max_tokens 4096 & c think_s1 --seed 1 --api_doc --think --max_tokens 16000 & wait
  kill $S ) &
wait
echo "S2_N10 runs done $(date)" >> results/queue_log.txt
