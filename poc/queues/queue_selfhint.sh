#!/bin/bash
# Non-oracle versions of the text hint (review item 10 "fixes are partly oracle"):
#  self_hint = the model first names the standard algorithm + key formula (1-2 sentences, no helpers shown), then codes with its own plan;
#  hint_retrieve = BM25 top-1 from an 11-entry algorithm library (offline check: right entry for rectunion/close only; hull & lattice
#  retrieve "ray casting", area2 retrieves "Pick's theorem" = realistic misfires).
# Tasks: hard (lattice, rectunion, no toolbox), hull with the E4 HIGH helpers, area2 (no toolbox). 8B GPU0 / 32B GPU1 / Llama-70B GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
HI='{"hull": ["polar_sort", "collinear"]}'
lane() { S=$(poc/start_server.sh $1 $2 $3 $4 $5) || { echo "$5 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$6; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  for h in self_hint hint_retrieve; do
    $P poc/run_geo_cross.py --model_tag H_geox${m}_hard_${h}_t07s1 --tasks lattice,rectunion $X --$h > results/run_H_geox${m}_hard_$h.log 2>&1
    $P poc/run_geo_cross.py --model_tag H_geox${m}_hullhi_${h}_t07s1 --tasks hull $X --distract 0 --distract_set "$HI" --$h > results/run_H_geox${m}_hullhi_$h.log 2>&1
  done
  $P poc/run_geo_cross.py --model_tag H_geox${m}_area2_hint_retrieve_t07s1 --tasks area2 $X --hint_retrieve > results/run_H_geox${m}_area2_hr.log 2>&1
  $P poc/run_geo_cross.py --model_tag H_geox${m}_area2_base_t07s1 --tasks area2 $X > results/run_H_geox${m}_area2_base.log 2>&1
  [ "$m" = "l70" ] && $P poc/run_geo_cross.py --model_tag H_geox${m}_hull_k0_t07s1 --tasks hull $X --distract 0 > results/run_H_geox${m}_hull_k0.log 2>&1
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-8B 8096 0 0.45 q8b_selfhint 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8097 1 0.45 q32b_selfhint 32b & L2=$!
sleep 30
lane /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8098 3 0.7 llama70_selfhint l70 & L3=$!
wait $L1 $L2 $L3
echo SELFHINT_DONE >> results/queue_log.txt
