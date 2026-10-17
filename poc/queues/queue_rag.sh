#!/bin/bash
# RAG experiments (user question "does adding context like RAG solve the problems?"):
#  (A) CO: BM25 retrieval over a titled snippet library: top-1 titled (= oracle snippet in practice), top-3 titled (oracle + near-miss,
#      e.g. CVRP + TSP snippet), top-3 code-only (weak retriever: top-1 is an unneeded API line; knapsack snippet never retrieved).
#      main 4 + held-out 2 problems (n_inst 18, 360 inst) and CVRP (n_inst 10, 30 inst); solver arm, repair 2, T=0.7 s1.
#  (B) geometry: TEXT algorithm hints instead of helper code: hard tasks (lattice/rectunion) with hint, no toolbox; hull with the E4 HIGH
#      helpers (polar_sort, collinear) + hint (does a text hint counter the steering?).
# Qwen3-8B (GPU 0), Qwen3-32B-AWQ (GPU 1), Llama-3.3-70B-w4a16 (GPU 3, 0.7).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
HI='{"hull": ["polar_sort", "collinear"]}'
lane() { S=$(poc/start_server.sh $1 $2 $3 $4 $5) || { echo "$5 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$6
  C="--arms solver --repair 2 --temperature 0.7 --seed 1"
  for r in "1 t1" "3 t3" "3 nt3"; do set -- $r; k=$1; tag=$2; nt=""; [ "${tag:0:2}" = "nt" ] && nt="--retrieve_notitle"
    $P poc/run_co.py --model_tag G_co${m}_rag${tag} $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 18 --retrieve $k $nt > results/run_G_co${m}_rag${tag}.log 2>&1
    $P poc/run_co.py --model_tag G_coV${m}_rag${tag} $C --probs cvrp --n_inst 10 --retrieve $k $nt > results/run_G_coV${m}_rag${tag}.log 2>&1
  done
  if [ "$m" = "l70" ]; then $P poc/run_co.py --model_tag G_co${m}_doctask $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 18 --api_doc --api_doc_task > results/run_G_co${m}_doctask.log 2>&1; fi
  X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  $P poc/run_geo_cross.py --model_tag H_geox${m}_hard_hint_t07s1 --tasks lattice,rectunion $X --algo_hint > results/run_H_geox${m}_hard_hint.log 2>&1
  $P poc/run_geo_cross.py --model_tag H_geox${m}_hullhi_hint_t07s1 --tasks hull $X --distract 0 --distract_set "$HI" --algo_hint > results/run_H_geox${m}_hullhi_hint.log 2>&1
  $P poc/run_geo_cross.py --model_tag H_geox${m}_hullhi_t07s1 --tasks hull $X --distract 0 --distract_set "$HI" > results/run_H_geox${m}_hullhi.log 2>&1
  $P poc/run_geo_cross.py --model_tag H_geox${m}_hull_hint_t07s1 --tasks hull $X --algo_hint > results/run_H_geox${m}_hull_hint.log 2>&1
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-8B 8096 0 0.45 q8b_rag 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8097 1 0.45 q32b_rag 32b & L2=$!
sleep 30
lane /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8098 3 0.7 llama70_rag l70 & L3=$!
wait $L1 $L2 $L3
echo RAG_DONE >> results/queue_log.txt
