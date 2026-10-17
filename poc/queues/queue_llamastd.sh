#!/bin/bash
# Llama geometry: all 29 crashes in the T=0.3 runs were `import shapely` (not installed). State the environment fact (stdlib only):
# greedy + T=0.3 x5 seeds, then MR-select offline.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8088 llama8b_std 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8088/v1
$P poc/run_geo_cross.py --model_tag geoxllama8b_std --stdlib --max_tokens 2048 > results/run_geoxllama8b_std.log 2>&1
$P poc/run_geo_cross.py --model_tag geoxllama8b_std_prims_task --stdlib --primitives --prims_task --max_tokens 2048 > results/run_geoxllama8b_std_prims_task.log 2>&1
for sd in 1 2 3 4 5; do
  $P poc/run_geo_cross.py --model_tag geoxllama8b_std03_t07s$sd --stdlib --temperature 0.3 --seed $sd --max_tokens 2048 > results/run_geoxllama8b_std03_s$sd.log 2>&1
done
kill $S
echo LLAMASTD_DONE >> results/queue_distract.log
