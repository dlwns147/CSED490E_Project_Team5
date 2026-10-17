#!/bin/bash
# Seed-3 replication of N15 (synthetic library choice) and N14c (job-shop + release dates), one model per GPU.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 port=$2 gpu=$3 tag=$4 mt=$5 eff=$6 rdsrc=$7 extra=$8
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 rep3_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  C="--n_inst 4 --temperature 0.7 --fmt_fix --max_tokens $mt"; ALL=knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw
  for L in free cpsat mip; do $P poc/run_co.py --model_tag S2_N15_${tag}_${L}_s3 --arms solver --probs $ALL --lib $L --seed 3 $C > results/run_S2_N15_${tag}_${L}_s3.log 2>&1 & done
  $P poc/run_co.py --model_tag S2_N15_${tag}_routing_s3 --arms solver --probs tsp,cvrp,vrptw --lib routing --seed 3 $C > results/run_S2_N15_${tag}_routing_s3.log 2>&1 &
  $P poc/run_co.py --model_tag S2_N15_${tag}_none_s3 --arms heuristic --probs $ALL --seed 3 $C > results/run_S2_N15_${tag}_none_s3.log 2>&1 &
  wait
  NOTE="solves job-shop scheduling without release dates"
  $P poc/run_jssp_rd.py run ${tag}_scratch 3 --max_tokens $mt > results/h5/rd/run_${tag}_scratch_3.log 2>&1 &
  $P poc/run_jssp_rd.py run ${tag}_good 3 --max_tokens $mt --adapt $rdsrc --note "$NOTE" > results/h5/rd/run_${tag}_good_3.log 2>&1 &
  [ $tag = q32b ] && $P poc/run_jssp_rd.py run ${tag}_goodmin 3 --max_tokens $mt --minimal --adapt $rdsrc --note "$NOTE" > results/h5/rd/run_${tag}_goodmin_3.log 2>&1 &
  wait
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 q32b 4096 "" results/h5/rd/src_q32b_plain_good.py "" &
lane /SSD/huggingface/openai/gpt-oss-20b 8044 1 oss20 16000 low results/h5/rd/src_oss20_low_plain_good.py "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 2 q36 8192 "" results/h5/rd/src_q36_plain_good.py "--max-num-seqs 64 --language-model-only" &
lane /SSD/huggingface/openai/gpt-oss-120b 8046 3 oss120 16000 low results/h5/rd/src_oss120_low_plain_good.py "" &
wait
echo "S2_REP3 runs done $(date)" >> results/queue_log.txt
