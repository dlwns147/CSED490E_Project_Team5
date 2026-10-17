#!/bin/bash
# 72B geometry re-run with --stdlib, PIPELINE-parallel over the 3 free GPUs (0,1,3) at 0.75 (~60 GB each, ~20 GB headroom), because a foreign
# 42 GB job has held GPU 2 for hours (TP must divide 64 heads, so TP3 is impossible). Port 8057 (range 8040-8099).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 1 120); do
  busy=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk 'NR!=3 && $1 > 10000' | wc -l)
  [ "$busy" -eq 0 ] && break; sleep 300
done
[ "$busy" -eq 0 ] || { echo "72b_std: GPUs never freed ($(date))" >> results/gpu_choice.log; exit 1; }
curl -sf -m 3 localhost:8057/health >/dev/null 2>&1 && { echo "72b_std: port 8057 busy" >> results/gpu_choice.log; exit 1; }
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen2.5-72B-Instruct 8057 0,1,3 0.75 --pipeline-parallel-size 3 > results/server_vllm_q72b_std.log 2>&1 9>&- &
S=$!; echo "q72b_std: GPUs 0,1,3 frac 0.75 PP3 port 8057 ($(date))" >> results/gpu_choice.log
until curl -sf localhost:8057/health >/dev/null; do kill -0 $S 2>/dev/null || { echo "q72b_std failed" >> results/gpu_choice.log; exit 1; }; sleep 10; done
curl -s localhost:8057/v1/models | grep -q "Qwen2.5-72B" || { echo "q72b_std: wrong model on 8057" >> results/gpu_choice.log; kill $S; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8057/v1
$P poc/run_geo_cross.py --model_tag geox72b_std --stdlib --max_tokens 2048 > results/run_geox72b_std.log 2>&1
$P poc/run_geo_cross.py --model_tag geox72b_std_prims_task --stdlib --primitives --prims_task --max_tokens 2048 > results/run_geox72b_std_prims_task.log 2>&1
kill $S
echo Q72BSTD_DONE >> results/queue_72b.log
