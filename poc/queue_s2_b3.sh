#!/bin/bash
# B3 (results/PREREG_B3.md). Qwen3-8B on 8040/8042 (GPUs 0, 2), Qwen3-32B-AWQ on 8041/8043 (GPUs 1, 3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
r() { port=$1 tag=$2; shift 2; POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1; }
LOW='{"diameter": ["point_in_polygon", "segments_intersect"]}'
for sd in 1 2; do
  pa=$([ $sd = 1 ] && echo 8040 || echo 8042); pb=$([ $sd = 1 ] && echo 8041 || echo 8043)
  r $pa S2_B3_geox8b_k8scope_t07s$sd --seed $sd --distract 8 --scope_note &
  r $pa S2_B3_geox8b_k8s2a_t07s$sd --seed $sd --distract 8 --s2a &
  r $pb S2_B3_geox32b_k8scope_t07s$sd --seed $sd --distract 8 --scope_note &
  r $pb S2_B3_geox32b_k8s2a_t07s$sd --seed $sd --distract 8 --s2a &
  r $pb S2_B3_geox32b_diamlowscope_t07s$sd --seed $sd --tasks diameter --distract 0 --distract_set "$LOW" --scope_note &
  r $pb S2_B3_geox32b_diamlows2a_t07s$sd --seed $sd --tasks diameter --distract 0 --distract_set "$LOW" --s2a &
done
for m in "8b 8042" "32b 8043"; do set -- $m
  for j in 0 1 2; do
    doc=$($P -c "import json; print(json.load(open('results/draft_docs_$1.json'))[$j]['doc'])")
    r $2 S2_B3_geox$1_deldraft$((j+1))_t07s1 --seed 1 --tasks delaunay --distract 0 --incircle_comment "$doc" &
  done
done
wait
echo "S2_B3 runs done $(date)" >> results/queue_log.txt
