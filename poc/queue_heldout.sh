#!/bin/bash
# HELD-OUT geometry tasks (convex, tri; designed after all findings): do the toolbox findings and the verified-sampling fix generalise?
# (stdlib-only environment fact: models otherwise import shapely, which is not installed)
# arms: no helpers (seeds 1-3, for MR-select), task-matched (orient), all 4 original predicates, K=8 related distractors; 8B/14B/32B; T=0.7
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  ss -ltn | grep -q ":$2 " && { echo "port $2 busy, abort lane $4"; return 1; }   # never share a port with another session
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  H="--tasks convex,tri --n_inst 20 --temperature 0.7 --max_tokens 4096 --stdlib"
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag geoxHO${m}_base_t07s$sd $H --seed $sd > results/run_geoxHO${m}_base_t07s$sd.log 2>&1; done
  for sd in 1 2; do
    $P poc/run_geo_cross.py --model_tag geoxHO${m}_dis0_t07s$sd $H --seed $sd --distract 0 > results/run_geoxHO${m}_dis0_t07s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag geoxHO${m}_prims_t07s$sd $H --seed $sd --primitives > results/run_geoxHO${m}_prims_t07s$sd.log 2>&1
    $P poc/run_geo_cross.py --model_tag geoxHO${m}_dis8_t07s$sd $H --seed $sd --distract 8 > results/run_geoxHO${m}_dis8_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8101 q8b_ho 8b; lane /SSD/huggingface/Qwen/Qwen3-14B 8102 q14b_ho 14b ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8103 q32b_ho 32b & L2=$!
wait $L1 $L2
echo HELDOUT_DONE >> results/queue_distract.log
