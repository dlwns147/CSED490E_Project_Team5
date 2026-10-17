#!/bin/bash
# Review item 3: polygon clipping task ("clip": twice the exact rational area of the intersection of two convex polygons, printed as p/q).
# Qwen3-8B (GPU 1), Qwen3-32B-AWQ (GPU 3), then gpt-oss-20b low (GPU 1) and Llama-70B (GPU 3): no toolbox s1-3 (MR-select), K0 (orient),
# K8, text hint (Sutherland-Hodgman); Qwen also thinking. n_inst 30 x sizes (6, 10) = 60 programs per arm, T=0.7.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { S=$(poc/start_server.sh $1 $2 $3 $4 $5) || { echo "$5 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$6; [ -n "$7" ] && export POC_REASONING_EFFORT=$7 || unset POC_REASONING_EFFORT
  X="--tasks clip --stdlib --n_inst 30 --max_tokens 16000 --temperature 0.7"
  for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag C2_geox${m}_base_t07s$sd $X --seed $sd > results/run_C2_${m}_base_s$sd.log 2>&1; done
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag C2_geox${m}_dis${k}_t07s1 $X --seed 1 --distract $k > results/run_C2_${m}_dis$k.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag C2_geox${m}_hint_t07s1 $X --seed 1 --algo_hint > results/run_C2_${m}_hint.log 2>&1
  if [ "${m:0:1}" = "q" ]; then $P poc/run_geo_cross.py --model_tag C2_geox${m}_think_t07s1 $X --seed 1 --think --max_tokens 20000 > results/run_C2_${m}_think.log 2>&1; fi
  kill $S; sleep 15; }
( lane /SSD/huggingface/Qwen/Qwen3-8B 8069 1 0.45 q8b_clip q8b; lane /SSD/huggingface/openai/gpt-oss-20b 8069 1 0.45 oss20_clip oss20low low ) & A=$!
sleep 30
( lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8070 3 0.45 q32b_clip q32b; lane /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8070 3 0.7 llama70_clip l70 ) & B=$!
wait $A $B
echo CLIP_DONE >> results/queue_log.txt
