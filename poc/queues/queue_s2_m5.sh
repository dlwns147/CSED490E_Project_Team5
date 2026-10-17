#!/bin/bash
# M5 (docs/prereg/PREREG_M5.md): re-run M4 storing the draft. Lanes: 8B s1 8040, 8B s2 8042, 32B s1 8041, 32B s2 8043.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --distract 8 --algo_first"
lane() { m=$1 sd=$2 port=$3; export POC_BASE_URL=http://127.0.0.1:$port/v1
  r() { tag=S2_M5_geox${m}_$1_t07s$sd; shift; $P poc/run_geo_cross.py --model_tag $tag $X --seed $sd "$@" > results/run_$tag.log 2>&1; }
  r core_m4 --tasks hull,area2,pip,segs,close & r del_m4 --tasks delaunay --incircle fixed & r lat_m4 --tasks lattice --area_helper abs &
  wait; echo "S2_M5 lane $m s$sd done $(date)" >> results/queue_log.txt; }
( lane 8b 1 8040 ) & A=$!; ( lane 8b 2 8042 ) & B=$!; ( lane 32b 1 8041 ) & C=$!; ( lane 32b 2 8043 ) & D=$!
for p in $A $B $C $D; do while kill -0 $p 2>/dev/null; do sleep 30; done; done
echo S2_M5_DONE >> results/queue_log.txt
