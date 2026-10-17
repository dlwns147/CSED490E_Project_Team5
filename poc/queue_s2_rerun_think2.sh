#!/bin/bash
# Second re-run of the thinking arms, now resumable (servers died again at 01:59 / 02:25 on 2026-10-17: NCCL watchdog starved for
# 480 s while the host load average was ~2,800 and swap was full). Each lane retries up to 6 times, keeping finished rows.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix"
lines() { [ -f "$1" ] && wc -l < "$1" || echo 0; }
u1() { model=$1 port=$2 gpu=$3 tag=$4 tmt=$5 extra=$6
  G=results/geocross_S2_U1_${tag}_geo_think_s1.jsonl; C=results/co_S2_U1_${tag}_co_think_s1.jsonl
  for att in 1 2 3 4 5 6; do
    [ $(lines $G) -ge 108 ] && [ $(lines $C) -ge 100 ] && break
    S=$(bash poc/start_server.sh $model $port $gpu 0.88 rr2_u1_${tag}_$att $extra) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1
    [ $(lines $G) -ge 108 ] || $P poc/run_geo_cross.py --model_tag S2_U1_${tag}_geo_think_s1 $GX --seed 1 --distract 8 --think --max_tokens $tmt --resume >> results/run_S2_U1_${tag}_geo_think_s1.log 2>&1 &
    [ $(lines $C) -ge 100 ] || $P poc/run_co.py --model_tag S2_U1_${tag}_co_think_s1 $CX --seed 1 --api_doc --think --max_tokens $tmt --resume >> results/run_S2_U1_${tag}_co_think_s1.log 2>&1 &
    wait; kill $S 2>/dev/null; sleep 30
  done
  echo "S2_U1 think $tag: geo $(lines $G)/108, co $(lines $C)/100 $(date)" >> results/queue_log.txt; }
x1() { for att in 1 2 3 4 5 6; do
    n=0; for sd in 1 2 3; do n=$((n + $(lines results/x1/math_q32b_think_s$sd.jsonl))); done; [ $n -ge 1680 ] && break
    S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8061 1 0.88 rr2_x1_q32b_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:8061/v1
    for sd in 1 2 3; do $P poc/run_math.py q32b think $sd --think --max_tokens 28000 >> results/x1/run_q32b_think_s$sd.log 2>&1 & done; wait
    kill $S 2>/dev/null; sleep 30
  done
  echo "S2_X1 q32b thinking: $(cat results/x1/math_q32b_think_s*.jsonl | wc -l)/1680 rows $(date)" >> results/queue_log.txt; }
u1 /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8058 0 q32b 16000 "" &
u1 /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8059 2 q36 28000 "--max-num-seqs 64 --language-model-only" &
u1 /SSD/huggingface/Qwen/Qwen3-8B 8060 3 q8b 16000 "" &
x1 &
wait
echo "S2 resumable thinking re-run finished $(date)" >> results/queue_log.txt
