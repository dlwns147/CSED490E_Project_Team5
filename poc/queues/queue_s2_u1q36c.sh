#!/bin/bash
# U1-Q36C (docs/prereg/PREREG_U1.md): Qwen3.6 THINK arm of U1 re-run with the model card's sampling, 80k cap, seeds 1-3; GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_TIMEOUT=14400 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter --resume"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --resume"
for att in 1 2 3 4; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8067 3 0.88 u1q36c_$att --max-num-seqs 64 --language-model-only --max-model-len 90000) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8067/v1
  for sd in 1 2 3; do
    t=S2_U1_q36c_geo_think_s$sd; $P poc/run_geo_cross.py --model_tag $t $GX --seed $sd --distract 8 --think --max_tokens 80000 >> results/run_$t.log 2>&1 &
    t=S2_U1_q36c_co_think_s$sd; $P poc/run_co.py --model_tag $t $CX --seed $sd --api_doc --think --max_tokens 80000 >> results/run_$t.log 2>&1 &
  done; wait
  kill $S; sleep 20
  n=$(cat results/geocross_S2_U1_q36c_geo_think_s*.jsonl results/co_S2_U1_q36c_co_think_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 624 ] && break
done
echo "S2_U1Q36C done ($n/624 rows) $(date)" >> results/queue_log.txt
for s in 1 2 3; do U1_THINK_M=q36c U1_CURE_SEED=$( [ $s = 1 ] && echo "" || echo $s ) timeout 1800 $P poc/analyze_u1.py q36 > results/u1_q36c_cure$s.log 2>&1; done
echo "S2_U1Q36C analysis -> results/u1_q36c_cure{1,2,3}.log $(date)" >> results/queue_log.txt
