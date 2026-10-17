#!/bin/bash
# N10-M3 (docs/prereg/PREREG_N10.md): the fix-menu factorial with Qwen3.6-35B-A3B-FP8 no-think (thinking fix = thinking on, 16k).
# Geometry lane: 8041 on GPU 1. Optimization lane: 8045 on GPU 3. Tags S2_N10m3_geo_<arm> / S2_N10m3_co_<arm>. Catalog bug already fixed.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
M=/SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8
GT="hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks $GT"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix"
g() { tag=S2_N10m3_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $GX "$@" > results/run_$tag.log 2>&1; }
c() { tag=S2_N10m3_co_$1; shift; $P poc/run_co.py --model_tag $tag $CX "$@" > results/run_$tag.log 2>&1; }
( S=$(bash poc/start_server.sh $M 8041 1 0.88 n10m3_geo --max-num-seqs 64 --language-model-only) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8041/v1
  g k8_s1 --seed 1 --distract 8 --max_tokens 8192 & g k8_s2 --seed 2 --distract 8 --max_tokens 8192 &
  g k8_s3 --seed 3 --distract 8 --max_tokens 8192 & g none_s1 --seed 1 --max_tokens 8192 &
  g auto_s1 --seed 1 --distract 8 --autoscope --max_tokens 8192 & wait
  g stdin_s1 --seed 1 --distract 8 --show_stdin --max_tokens 8192 & g plan_s1 --seed 1 --distract 8 --self_hint --max_tokens 8192 &
  g k0_s1 --seed 1 --distract 0 --max_tokens 8192 & g think_s1 --seed 1 --distract 8 --think --max_tokens 16000 & wait
  kill $S ) &
( S=$(bash poc/start_server.sh $M 8045 3 0.88 n10m3_co --max-num-seqs 64 --language-model-only) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8045/v1
  c doc_s1 --seed 1 --api_doc --max_tokens 8192 & c doc_s2 --seed 2 --api_doc --max_tokens 8192 &
  c doc_s3 --seed 3 --api_doc --max_tokens 8192 & c nodoc_s1 --seed 1 --max_tokens 8192 &
  c rag3_s1 --seed 1 --retrieve 3 --max_tokens 8192 & wait
  c stdin_s1 --seed 1 --api_doc --show_stdin --max_tokens 8192 & c repair_s1 --seed 1 --api_doc --repair 1 --max_tokens 8192 &
  c snippet_s1 --seed 1 --api_doc --api_doc_task --max_tokens 8192 & c think_s1 --seed 1 --api_doc --think --max_tokens 16000 & wait
  kill $S ) &
wait
echo "S2_N10m3 runs done $(date)" >> results/queue_log.txt
