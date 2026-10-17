#!/bin/bash
# E2 extension (registered in docs/prereg/PREREG_E2.md, 13:20): delaunay hidden contract for Llama-3.3-70B / Qwen3-14B (no thinking) and
# Qwen3-8B / 32B with thinking. Servers: 8040 Qwen3-8B (GPU 0), 8041 Qwen3-32B-AWQ (GPU 1), 8042 Qwen3-14B (GPU 2), 8043 Llama-70B (GPU 3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
r() { port=$1 m=$2 cond=$3 sd=$4; shift 4; tag=S2_E2_geox${m}_${cond}_t07s$sd
  POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_geo_cross.py --model_tag $tag --stdlib --n_inst 30 --temperature 0.7 --seed $sd --tasks delaunay "$@" > results/run_$tag.log 2>&1; }
for sd in 1 2; do
  for pm in "8043 l70" "8042 14b"; do set -- $pm
    r $1 $2 del_none $sd --max_tokens 4096 &
    for v in signed doc fixed; do r $1 $2 del_$v $sd --max_tokens 4096 --distract 0 --incircle $v & done
  done
  for pm in "8040 8bthink" "8041 32bthink"; do set -- $pm
    for v in signed fixed; do r $1 $2 del_$v $sd --max_tokens 16000 --think --distract 0 --incircle $v & done
  done
done
wait
echo "S2_E2x done $(date)" >> results/queue_log.txt
