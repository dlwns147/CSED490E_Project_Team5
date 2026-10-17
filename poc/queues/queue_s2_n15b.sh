#!/bin/bash
# N15 addendum: gpt-oss-120b low on 8046 GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8046 3 0.88 n15_oss120) || exit 1
export POC_BASE_URL=http://127.0.0.1:8046/v1 POC_REASONING_EFFORT=low
C="--n_inst 4 --temperature 0.7 --fmt_fix --max_tokens 16000"; ALL=knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw; tag=oss120
for sd in 1 2; do
  for L in free cpsat mip; do $P poc/run_co.py --model_tag S2_N15_${tag}_${L}_s$sd --arms solver --probs $ALL --lib $L --seed $sd $C > results/run_S2_N15_${tag}_${L}_s$sd.log 2>&1 & done
  $P poc/run_co.py --model_tag S2_N15_${tag}_routing_s$sd --arms solver --probs tsp,cvrp,vrptw --lib routing --seed $sd $C > results/run_S2_N15_${tag}_routing_s$sd.log 2>&1 &
  $P poc/run_co.py --model_tag S2_N15_${tag}_none_s$sd --arms heuristic --probs $ALL --seed $sd $C > results/run_S2_N15_${tag}_none_s$sd.log 2>&1 &
  $P poc/run_co.py --model_tag S2_N15_${tag}_default_s$sd --arms solver --probs $ALL --seed $sd $C > results/run_S2_N15_${tag}_default_s$sd.log 2>&1 &
  wait
done
kill $S
echo "S2_N15b (gpt-oss-120b) runs done $(date)" >> results/queue_log.txt
