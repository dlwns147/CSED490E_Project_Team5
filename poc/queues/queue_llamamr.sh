#!/bin/bash
# Cross-family check of the tool-free sampling fix: Llama-3.1-8B geometry programs, T=0.7, seeds 1-5 (MR-select offline)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8086 llama8b_mr 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8086/v1
for sd in 1 2 3 4 5; do
  $P poc/run_geo_cross.py --model_tag geoxllama8b_base_t07s$sd --temperature 0.7 --seed $sd --max_tokens 2048 > results/run_geoxllama8b_base_t07s$sd.log 2>&1
done
kill $S
echo LLAMAMR_DONE >> results/queue_distract.log
