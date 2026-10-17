#!/bin/bash
# M2 / M3 / M4 and baselines (docs/prereg/PREREG_M2_M4.md). One lane per (model, seed):
#   8B s1 -> 8040 (GPU 0), 8B s2 -> 8042 (GPU 2), 32B s1 -> 8041 (GPU 1), 32B s2 -> 8043 (GPU 3).
# Groups: core = hull,area2,pip,segs,close (C1 settings); del = delaunay (--incircle fixed); lat = lattice (--area_helper abs).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
lane() { m=$1 sd=$2 port=$3; export POC_BASE_URL=http://127.0.0.1:$port/v1
  r() { tag=S2_MX_geox${m}_$1_t07s$sd; shift; $P poc/run_geo_cross.py --model_tag $tag $X --seed $sd "$@" > results/run_$tag.log 2>&1; }
  CORE="--tasks hull,area2,pip,segs,close"; DEL="--tasks delaunay --incircle fixed"; LAT="--tasks lattice --area_helper abs"
  # baselines + M4 (algorithm first) + M2 (auto contract) in parallel
  r core_bare $CORE & r lat_bare $LAT &
  r del_k8 $DEL --distract 8 & r lat_k8 $LAT --distract 8 & r lat_k0 $LAT --distract 0 &
  r core_think1024 $CORE --distract 8 --think_budget 1024 & r del_think1024 $DEL --distract 8 --think_budget 1024 & r lat_think1024 $LAT --distract 8 --think_budget 1024 &
  r core_m4 $CORE --distract 8 --algo_first & r del_m4 $DEL --distract 8 --algo_first & r lat_m4 $LAT --distract 8 --algo_first &
  r core_m4free $CORE --distract 8 --algo_first_free & r del_m4free $DEL --distract 8 --algo_first_free & r lat_m4free $LAT --distract 8 --algo_first_free &
  r del_m2 --tasks delaunay --distract 0 --auto_contract & r lat_m2 --tasks lattice --distract 0 --auto_contract &
  r lat_k0signed --tasks lattice --distract 0 & r lat_k0doc --tasks lattice --distract 0 --area_helper signed_doc &
  wait
  if [ "$m" = 8b ]; then   # M3: per-helper behavioural probe (drafts = the bare runs), then the final program with the kept helpers
    $P poc/helper_probe.py S2_MX_geox8b_core_bare_t07s$sd 8b_core_s$sd hull,area2,pip,segs,close 30 $sd > results/run_m3_core_s$sd.log 2>&1 &
    $P poc/helper_probe.py S2_E2_geox8b_del_none_t07s$sd 8b_del_s$sd delaunay 30 $sd > results/run_m3_del_s$sd.log 2>&1 &
    $P poc/helper_probe.py S2_MX_geox8b_lat_bare_t07s$sd 8b_lat_s$sd lattice 30 $sd > results/run_m3_lat_s$sd.log 2>&1 &
    wait
    r core_m3 $CORE --distract 8 --keep_json results/m3_keep_8b_core_s$sd.json &
    r del_m3 $DEL --distract 8 --keep_json results/m3_keep_8b_del_s$sd.json &
    r lat_m3 $LAT --distract 8 --keep_json results/m3_keep_8b_lat_s$sd.json &
    wait
  fi
  echo "S2_MX lane $m s$sd done $(date)" >> results/queue_log.txt; }
( lane 8b 1 8040 ) & A=$!
( lane 8b 2 8042 ) & B=$!
( lane 32b 1 8041 ) & C=$!
( lane 32b 2 8043 ) & D=$!
for p in $A $B $C $D; do while kill -0 $p 2>/dev/null; do sleep 30; done; done
echo S2_MX_DONE >> results/queue_log.txt
