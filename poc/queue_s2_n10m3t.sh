#!/bin/bash
# N10-M3 thinking arm re-run (setup failure: Qwen3.6 thinking hit the 16k cap on 102 / 108 geometry and 52 / 100 optimization items;
# old files kept as *_think_s1_cap16k.jsonl). 48k cap, max-model-len 65536. 8041 GPU 1 geometry, 8045 GPU 3 optimization.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
M=/SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8
X="--max-num-seqs 64 --language-model-only --max-model-len 65536"
( S=$(bash poc/start_server.sh $M 8041 1 0.88 n10m3t_geo $X) || exit 1
  POC_BASE_URL=http://127.0.0.1:8041/v1 $P poc/run_geo_cross.py --model_tag S2_N10m3_geo_think_s1 --stdlib --n_inst 6 --temperature 0.7 \
    --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter --seed 1 --distract 8 --think --max_tokens 48000 > results/run_S2_N10m3_geo_think_s1.log 2>&1
  kill $S ) &
( S=$(bash poc/start_server.sh $M 8045 3 0.88 n10m3t_co $X) || exit 1
  POC_BASE_URL=http://127.0.0.1:8045/v1 $P poc/run_co.py --model_tag S2_N10m3_co_think_s1 --arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw \
    --n_inst 4 --temperature 0.7 --fmt_fix --seed 1 --api_doc --think --max_tokens 48000 > results/run_S2_N10m3_co_think_s1.log 2>&1
  kill $S ) &
wait
echo "S2_N10m3t (thinking re-run, 48k) done $(date)" >> results/queue_log.txt
