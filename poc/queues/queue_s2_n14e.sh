#!/bin/bash
# N14e (PREREG_N14.md): two more job-shop rungs. Qwen3-32B-AWQ 8042 GPU2, gpt-oss-120b low 8046 GPU3. References on CPU (run_jssp_var.py <v> ref).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 port=$2 gpu=$3 tag=$4 src=$5 mt=$6 eff=$7
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 n14e_$tag) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  NOTE="solves classic job-shop scheduling (each operation on one given machine, makespan objective)"
  for sd in 1 2; do
    r() { v=$1 t=$2; shift 2; $P poc/run_jssp_var.py $v run ${tag}_$t $sd --max_tokens $mt "$@" > results/h5/$v/run_${tag}_${t}_$sd.log 2>&1; }
    r tard scratch & r tard adapt --minimal --adapt $src --note "$NOTE" &
    r flex scratch & r flex adapt --minimal --adapt $src --note "$NOTE" &
    r flex snip --snippet & r flex adaptsnip --snippet --minimal --adapt $src --note "$NOTE" &
    wait
  done
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8042 2 q32b results/h5/rd/src_q32b_plain_good.py 8000 "" &
lane /SSD/huggingface/openai/gpt-oss-120b 8046 3 oss120 results/h5/rd/src_oss120_low_plain_good.py 16000 low &
wait
echo "S2_N14e runs done $(date)" >> results/queue_log.txt
