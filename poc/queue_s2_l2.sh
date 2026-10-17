#!/bin/bash
# L2 (results/PREREG_L1.md extension): API-only library + "exactly these functions" sentence. 8040 Qwen3-8B, 8041 Qwen3-32B-AWQ.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --tb_api --api_only_note"
for mp in "8b 8040" "32b 8041"; do
  set -- $mp
  for k in 0 8; do for sd in 1 2; do
    POC_BASE_URL=http://127.0.0.1:$2/v1 $P poc/run_geo_cross.py --model_tag S2_L2_geox$1_apionly_k${k}_t07s$sd $X --seed $sd --distract $k > results/run_S2_L2_$1_k${k}_s$sd.log 2>&1 &
  done; done
done
wait
echo "S2_L2 runs done $(date)" >> results/queue_log.txt
