#!/bin/bash
# U1r (PREREG_U1.md): seeds 2-3 of the U1 cure arms. Resumable; each lane retries up to 4 times.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter --resume"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --resume"
lane() { model=$1 port=$2 gpu=$3 tag=$4 tmt=$5 extra=$6
  for att in 1 2 3 4; do
    S=$(bash poc/start_server.sh $model $port $gpu 0.88 u1r_${tag}_$att $extra) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1
    g() { t=S2_U1_${tag}_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $t $GX "$@" >> results/run_$t.log 2>&1; }
    c() { t=S2_U1_${tag}_co_$1; shift; $P poc/run_co.py --model_tag $t $CX "$@" >> results/run_$t.log 2>&1; }
    for sd in 2 3; do
      g fact_s$sd --seed $sd --distract 0 --algo_hint --max_tokens 4096 & g decor_s$sd --seed $sd --max_tokens 4096 &
      c fact_s$sd --seed $sd --api_doc --api_doc_task --max_tokens 4096 & c decor_s$sd --seed $sd --retrieve 3 --max_tokens 4096 &
    done; wait
    for sd in 2 3; do g think_s$sd --seed $sd --distract 8 --think --max_tokens $tmt & c think_s$sd --seed $sd --api_doc --think --max_tokens $tmt & done; wait
    kill $S; sleep 20
    n=$(cat results/geocross_S2_U1_${tag}_geo_think_s3.jsonl results/co_S2_U1_${tag}_co_think_s3.jsonl results/geocross_S2_U1_${tag}_geo_think_s2.jsonl results/co_S2_U1_${tag}_co_think_s2.jsonl 2>/dev/null | wc -l)
    [ "$n" -ge 416 ] && break
  done
  echo "S2_U1r $tag done ($n/416 think rows) $(date)" >> results/queue_log.txt; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 q32b 16000 "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 2 q36 28000 "--max-num-seqs 64 --language-model-only" &
lane /SSD/huggingface/Qwen/Qwen3-8B 8056 3 q8b 16000 "" &
wait
echo "S2_U1r runs done $(date)" >> results/queue_log.txt
