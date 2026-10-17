#!/bin/bash
# B1 (results/PREREG_B1.md): candidates with top-20 log-probs (3 seeds) + model-written tests. Qwen3-8B on 8040 (GPU 0) and 8041 (GPU 1).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --logprobs_topk 20"
g() { port=$1 tag=$2; shift 2; POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1; }
for sd in 1 2 3; do
  g 8040 S2_B1_geox8b_dis0_t07s$sd --seed $sd --distract 0 &
  g 8041 S2_B1_geox8b_dis8_t07s$sd --seed $sd --distract 8 &
  g 804$((sd % 2)) S2_B1_geox8b_hard_t07s$sd --seed $sd --tasks lattice,rectunion &
done
POC_BASE_URL=http://127.0.0.1:8040/v1 $P poc/gen_tests.py S2_B1_core hull,area2,pip,segs,close > results/run_S2_B1_tests_core.log 2>&1 &
POC_BASE_URL=http://127.0.0.1:8041/v1 $P poc/gen_tests.py S2_B1_hard lattice,rectunion > results/run_S2_B1_tests_hard.log 2>&1 &
wait
echo "S2_B1 data done $(date)" >> results/queue_log.txt
