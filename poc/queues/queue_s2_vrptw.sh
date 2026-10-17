#!/bin/bash
# Server 2 (2026-10-13), HANDOFF next step 2: VRPTW with the instance's literal stdin in the prompt (--show_stdin), GPUs 0-3.
# Servers are started separately (start_server.sh): 8040 gpt-oss-20b (GPU 0), 8041 gpt-oss-120b (GPU 1), 8042 Qwen3-32B-AWQ (GPU 2),
# 8043 Llama-3.3-70B w4a16 (GPU 3). Every lane first re-runs one old prose-only condition (VRPTW snippet, seed 1) on the new stack
# (vLLM 0.22) as a same-stack control, then the --show_stdin arms (no doc s1; VRPTW snippet s1-3). All tags carry the S2_ prefix.
# usage: bash poc/queues/queue_s2_vrptw.sh <pid-to-wait-for>   (the gpt-oss-20b low reproduction run)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
C="--arms solver --probs vrptw --n_inst 15 --repair 2 --temperature 0.7 --max_tokens 16000"
r() { tag=$1; shift; $P poc/run_co.py --model_tag S2_W_co$tag $C "$@" > results/run_S2_W_co$tag.log 2>&1; }
up() { for i in $(seq 90); do curl -sf -m 3 localhost:$1/health >/dev/null && return 0; sleep 20; done; return 1; }
lane() { port=$1 m=$2 eff=$3 ctrl=$4
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff || unset POC_REASONING_EFFORT
  up $port || { echo "S2_VRPTW lane $m: server $port not up $(date)" >> results/queue_log.txt; return; }
  [ "$ctrl" = 1 ] && r ${m}_doctask_s1 --seed 1 --api_doc --api_doc_task
  [ "$ctrl" = 1 ] && r ${m}_nodoc_ex --seed 1 --show_stdin
  for sd in ${SEEDS:-1 2 3}; do r ${m}_doctask_ex_s$sd --seed $sd --show_stdin --api_doc --api_doc_task; done
  echo "S2_VRPTW lane $m done $(date)" >> results/queue_log.txt; }
while kill -0 $1 2>/dev/null; do sleep 15; done
( SEEDS="2 3" lane 8040 oss20low low 0 ) & L1=$!
lane 8040 oss20med medium 1 & L2=$!
lane 8041 oss120low low 1 & L3=$!
lane 8041 oss120med medium 1 & L4=$!
lane 8042 q32b "" 1 & L5=$!
lane 8043 l70 "" 1 & L6=$!
for p in $L1 $L2 $L3 $L4 $L5 $L6; do while kill -0 $p 2>/dev/null; do sleep 30; done; done
echo S2_VRPTW_DONE >> results/queue_log.txt
