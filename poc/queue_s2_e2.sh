#!/bin/bash
# Server 2, E2 (pre-registered in results/PREREG_E2.md): F1 / F2 replication on two NEW tasks (delaunay, diameter).
# One lane per model; servers must already be up: 8044 Qwen3-8B, 8042 Qwen3-32B-AWQ, 8040 gpt-oss-20b (low effort).
# Tags: S2_E2_geox<m>_<cond>_t07s<seed>.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
up() { for i in $(seq 90); do curl -sf -m 3 localhost:$1/health >/dev/null && return 0; sleep 20; done; return 1; }
lane() { port=$1 m=$2 eff=$3
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff || unset POC_REASONING_EFFORT
  up $port || { echo "S2_E2 lane $m: server $port not up $(date)" >> results/queue_log.txt; return; }
  for sd in 1 2; do
    r() { tag=S2_E2_geox${m}_$1_t07s$sd; shift; $P poc/run_geo_cross.py --model_tag $tag $X --seed $sd "$@" > results/run_$tag.log 2>&1; }
    r del_none --tasks delaunay &
    r del_signed --tasks delaunay --distract 0 --incircle signed &
    r del_doc --tasks delaunay --distract 0 --incircle doc &
    r del_fixed --tasks delaunay --distract 0 --incircle fixed &
    r diam_k0 --tasks diameter &
    r diam_high --tasks diameter --distract 0 --distract_set '{"diameter": ["convex_hull", "polar_sort"]}' &
    r diam_low --tasks diameter --distract 0 --distract_set '{"diameter": ["point_in_polygon", "segments_intersect"]}' &
    wait   # this lane's own seven runs only (each lane is its own subshell)
  done
  echo "S2_E2 lane $m done $(date)" >> results/queue_log.txt; }
( lane 8044 8b "" ) & A=$!
( lane 8042 32b "" ) & B=$!
( lane 8040 oss20low low ) & C=$!
for p in $A $B $C; do while kill -0 $p 2>/dev/null; do sleep 30; done; done
echo S2_E2_DONE >> results/queue_log.txt
