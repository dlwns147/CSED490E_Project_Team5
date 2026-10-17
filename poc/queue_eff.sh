#!/bin/bash
# LLM-efficiency x CG/CO pilot on Qwen3-8B (one GPU, sequential servers):
#  (A) precision: bf16 vs fp8 weights (--quantization fp8, W8A16) vs fp8 KV cache (--kv-cache-dtype fp8) vs both; measured on geometry (tool-free s1, K=8 s1; n=300),
#      CO scoped snippet (84 inst) and held-out CO with thinking (long traces: where KV precision should matter most).
#  (B) compute frontier (bf16, token-accounted): K=8 geometry n=100 — no-think samples s4-s6 (for best-of-k) and thinking budgets 256/1024/4096 + full thinking.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
M=/SSD/huggingface/Qwen/Qwen3-8B
pickgpu() { while true; do G=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 5000 {print $1; exit}'); [ -n "$G" ] && { echo $G; return; }; sleep 120; done; }
runA() {  # runA <tag> <extra vllm args...>
  tag=$1; shift; G=$(pickgpu)
  S=$(poc/start_server.sh $M 8066 $G 0.45 q8b_$tag "$@") || { echo "$tag failed to start" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:8066/v1
  X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  $P poc/run_geo_cross.py --model_tag E_geox8b_${tag}_base $X > results/run_E_geox8b_${tag}_base.log 2>&1
  $P poc/run_geo_cross.py --model_tag E_geox8b_${tag}_dis8 $X --distract 8 > results/run_E_geox8b_${tag}_dis8.log 2>&1
  $P poc/run_co.py --model_tag E_co8b_${tag}_doctask --arms solver --api_doc_task --repair 2 --temperature 0.7 --seed 1 > results/run_E_co8b_${tag}_doctask.log 2>&1
  $P poc/run_co.py --model_tag E_coH8b_${tag}_doctask_think --arms solver --api_doc_task --repair 2 --probs binpack,vcover --n_inst 18 --temperature 0.7 --seed 1 --think --max_tokens 20000 > results/run_E_coH8b_${tag}_think.log 2>&1
  kill $S; sleep 20
}
runA bf16
runA fp8w --quantization fp8
runA fp8kv --kv-cache-dtype fp8
runA fp8both --quantization fp8 --kv-cache-dtype fp8
# (B) compute frontier, bf16
G=$(pickgpu); S=$(poc/start_server.sh $M 8067 $G 0.45 q8b_frontier) && {
  export POC_BASE_URL=http://127.0.0.1:8067/v1; X="--stdlib --distract 8 --temperature 0.7 --max_tokens 4096"
  for sd in 4 5 6; do $P poc/run_geo_cross.py --model_tag C_geox8b_dis8_s$sd $X --seed $sd > results/run_C_geox8b_dis8_s$sd.log 2>&1; done
  for B in 256 1024 4096; do $P poc/run_geo_cross.py --model_tag C_geox8b_dis8_b$B $X --seed 4 --think_budget $B > results/run_C_geox8b_dis8_b$B.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag C_geox8b_dis8_think --stdlib --distract 8 --temperature 0.7 --seed 4 --think --max_tokens 20000 > results/run_C_geox8b_dis8_think.log 2>&1
  kill $S; }
echo EFF_DONE >> results/queue_log.txt
