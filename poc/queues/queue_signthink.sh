#!/bin/bash
# Does reasoning avoid the signed-area trap? (R1-Distill-70B + K8 fell into it: 16/16 lattice transform failures = signed area w/o abs.)
# Qwen3-32B-AWQ then Qwen3-8B on GPU 1, lattice only, K0 (only polygon_area2), thinking on, T=0.7 s1: signed vs abs helper.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for mm in "Qwen3-32B-AWQ 32b" "Qwen3-8B 8b"; do set -- $mm
  S=$(poc/start_server.sh /SSD/huggingface/Qwen/$1 8092 1 0.45 q$2_signthink) || { echo "q$2_signthink failed" >> results/queue_log.txt; continue; }
  export POC_BASE_URL=http://127.0.0.1:8092/v1
  for ah in signed abs; do
    $P poc/run_geo_cross.py --model_tag S_geox$2_dis0_${ah}_think_t07s1 --tasks lattice --stdlib --n_inst 30 --temperature 0.7 --seed 1 --distract 0 --area_helper $ah --think --max_tokens 20000 > results/run_S_geox$2_${ah}_think.log 2>&1
  done
  kill $S; sleep 20
done
echo SIGNTHINK_DONE >> results/queue_log.txt
