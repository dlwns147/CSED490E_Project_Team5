#!/bin/bash
# N10-M2 (PREREG_N10.md): the fix-menu factorial with gpt-oss-20b (low effort; thinking fix = medium). 8043 GPU 0 geometry, 8042 GPU 2 optimization.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
M=/SSD/huggingface/openai/gpt-oss-20b
GT="hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks $GT --max_tokens 16000"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --max_tokens 16000"
g() { e=$1 tag=S2_N10m2_geo_$2; shift 2; POC_REASONING_EFFORT=$e $P poc/run_geo_cross.py --model_tag $tag $GX "$@" > results/run_$tag.log 2>&1; }
c() { e=$1 tag=S2_N10m2_co_$2; shift 2; POC_REASONING_EFFORT=$e $P poc/run_co.py --model_tag $tag $CX "$@" > results/run_$tag.log 2>&1; }
( S=$(bash poc/start_server.sh $M 8043 0 0.88 n10m2_geo) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8043/v1
  g low k8_s1 --seed 1 --distract 8 & g low k8_s2 --seed 2 --distract 8 & g low k8_s3 --seed 3 --distract 8 &
  g low none_s1 --seed 1 & g low auto_s1 --seed 1 --distract 8 --autoscope & wait
  g low stdin_s1 --seed 1 --distract 8 --show_stdin & g low plan_s1 --seed 1 --distract 8 --self_hint &
  g low k0_s1 --seed 1 --distract 0 & g medium think_s1 --seed 1 --distract 8 & wait
  kill $S ) &
( S=$(bash poc/start_server.sh $M 8042 2 0.88 n10m2_co) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8042/v1
  c low doc_s1 --seed 1 --api_doc & c low doc_s2 --seed 2 --api_doc & c low doc_s3 --seed 3 --api_doc &
  c low nodoc_s1 --seed 1 & c low rag3_s1 --seed 1 --retrieve 3 & wait
  c low stdin_s1 --seed 1 --api_doc --show_stdin & c low repair_s1 --seed 1 --api_doc --repair 1 &
  c low snippet_s1 --seed 1 --api_doc --api_doc_task & c medium think_s1 --seed 1 --api_doc & wait
  kill $S ) &
wait
echo "S2_N10m2 runs done $(date)" >> results/queue_log.txt
