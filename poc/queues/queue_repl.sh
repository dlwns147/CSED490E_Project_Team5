#!/bin/bash
# Replication (review item 4: single-seed cells) of the newest headline results, seed 2 (and 3 where cheap):
#  E5 mixed LoRA: main K0/K8 + held-out K8, seed 2 (GPU 0, merged model in /dev/shm/e5_mixed)
#  T8 text hints: hull HIGH helpers -/+ monotone-chain hint, hard tasks -/+ hint; seeds 2,3 (8B GPU 0 after E5, 32B GPU 1, Llama-70B GPU 3)
#  T8 RAG (CO): titled top-1 / top-3 on the 6 problems + CVRP, seed 2 (32B GPU 1, Llama-70B GPU 3)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
HI='{"hull": ["polar_sort", "collinear"]}'
hints() { m=$1
  for sd in 2 3; do X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed $sd"
    $P poc/run_geo_cross.py --model_tag H_geox${m}_hullhi_t07s$sd --tasks hull $X --distract 0 --distract_set "$HI" > results/run_H_geox${m}_hullhi_s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag H_geox${m}_hullhi_hint_t07s$sd --tasks hull $X --distract 0 --distract_set "$HI" --algo_hint > results/run_H_geox${m}_hullhi_hint_s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag H_geox${m}_hard_t07s$sd --tasks lattice,rectunion $X > results/run_H_geox${m}_hard_s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag H_geox${m}_hard_hint_t07s$sd --tasks lattice,rectunion $X --algo_hint > results/run_H_geox${m}_hard_hint_s$sd.log 2>&1
  done; }
rag() { m=$1; C="--arms solver --repair 2 --temperature 0.7 --seed 2"
  for r in "1 t1" "3 t3"; do set -- $r
    $P poc/run_co.py --model_tag G_co${m}_rag$2_s2 $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 18 --retrieve $1 > results/run_G_co${m}_rag$2_s2.log 2>&1
    $P poc/run_co.py --model_tag G_coV${m}_rag$2_s2 $C --probs cvrp --n_inst 10 --retrieve $1 > results/run_G_coV${m}_rag$2_s2.log 2>&1
  done; }
laneA() { S=$(poc/start_server.sh /dev/shm/e5_mixed 8050 0 0.45 e5mixed_s2) && { export POC_BASE_URL=http://127.0.0.1:8050/v1
    X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 2"
    for k in 0 8; do $P poc/run_geo_cross.py --model_tag E5_geoxmixed_main_k${k}_s2 $X --distract $k > results/run_E5_mixed_main_k${k}_s2.log 2>&1; done
    $P poc/run_geo_cross.py --model_tag E5_geoxmixed_held_k8_s2 --tasks convex,tri,overlap $X --distract 8 > results/run_E5_mixed_held_k8_s2.log 2>&1
    kill $S; sleep 15; }
  S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8050 0 0.45 q8b_rep) && { export POC_BASE_URL=http://127.0.0.1:8050/v1
    $P poc/run_geo_cross.py --model_tag E5_geoxbase_held_k8_s2 --tasks convex,tri,overlap --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 2 --distract 8 > results/run_E5_base_held_k8_s2.log 2>&1
    hints 8b; kill $S; }; }
laneB() { S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8051 1 0.45 q32b_rep) && { export POC_BASE_URL=http://127.0.0.1:8051/v1; hints 32b; rag 32b; kill $S; }; }
laneC() { S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8052 3 0.7 llama70_rep) && { export POC_BASE_URL=http://127.0.0.1:8052/v1; hints l70; rag l70; kill $S; }; }
laneA & A=$!
sleep 30
laneB & B=$!
sleep 30
laneC & C=$!
wait $A $B $C
echo REPL_DONE >> results/queue_log.txt
