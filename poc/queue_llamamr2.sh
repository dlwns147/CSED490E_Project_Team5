#!/bin/bash
# Fair Llama setting for verified sampling: T=0.3 (T=0.7 samples crashed 22-29%), seeds 1-5
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct 8087 llama8b_mr2 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:8087/v1
for sd in 1 2 3 4 5; do
  $P poc/run_geo_cross.py --model_tag geoxllama8b_t03_t07s$sd --temperature 0.3 --seed $sd --max_tokens 2048 > results/run_geoxllama8b_t03_s$sd.log 2>&1
done
kill $S
echo LLAMAMR2_DONE >> results/queue_distract.log
