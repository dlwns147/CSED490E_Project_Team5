#!/bin/bash
# T7 causal test of the signed-area trap (lattice, K0 = only the needed helper polygon_area2, "should" header, T=0.7, seeds 1-2):
# same helper with an explicit sign warning (signed_doc) vs an unsigned helper returning abs() (abs). Baseline (signed, s1) = R_geox*_dis0_t07s1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
for mm in "Qwen3-8B 8b" "Qwen3-32B-AWQ 32b" "Qwen3-14B 14b"; do set -- $mm
  S=$(start /SSD/huggingface/Qwen/$1 8079 q$2_t7sign); export POC_BASE_URL=http://127.0.0.1:8079/v1
  for ah in signed_doc abs; do for sd in 1 2; do
    $P poc/run_geo_cross.py --model_tag S_geox$2_dis0_${ah}_t07s$sd --tasks lattice --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed $sd --distract 0 --area_helper $ah > results/run_S_geox$2_${ah}_s$sd.log 2>&1
  done; done
  $P poc/run_geo_cross.py --model_tag S_geox$2_dis0_signed_t07s2 --tasks lattice --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 2 --distract 0 > results/run_S_geox$2_signed_s2.log 2>&1
  kill $S; sleep 20
done
echo T7SIGN_DONE >> results/queue_log.txt
