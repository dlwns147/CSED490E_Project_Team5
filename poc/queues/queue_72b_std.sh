#!/bin/bash
# 72B geometry re-run with the environment fact (--stdlib): greedy base + task-matched. Waits (up to 10 h) until all 4 GPUs are nearly empty
# (TP4 at 0.6 = 48 GB/GPU, leaving ~32 GB headroom each), then uses port 8057 (this session's range 8040-8099).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 1 120); do
  busy=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 > 10000' | wc -l)
  [ "$busy" -eq 0 ] && break; sleep 300
done
[ "$busy" -eq 0 ] || { echo "72b_std: GPUs never freed ($(date))" >> results/gpu_choice.log; exit 1; }
curl -sf -m 3 localhost:8057/health >/dev/null 2>&1 && { echo "72b_std: port 8057 busy" >> results/gpu_choice.log; exit 1; }
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen2.5-72B-Instruct 8057 0,1,2,3 0.6 --tensor-parallel-size 4 > results/server_vllm_q72b_std.log 2>&1 9>&- &
S=$!; echo "q72b_std: GPUs 0-3 frac 0.6 TP4 port 8057 ($(date))" >> results/gpu_choice.log
until curl -sf localhost:8057/health >/dev/null; do kill -0 $S 2>/dev/null || { echo "q72b_std failed" >> results/gpu_choice.log; exit 1; }; sleep 10; done
curl -s localhost:8057/v1/models | grep -q "Qwen2.5-72B" || { echo "q72b_std: wrong model on 8057" >> results/gpu_choice.log; kill $S; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8057/v1
$P poc/run_geo_cross.py --model_tag geox72b_std --stdlib --max_tokens 2048 > results/run_geox72b_std.log 2>&1
$P poc/run_geo_cross.py --model_tag geox72b_std_prims_task --stdlib --primitives --prims_task --max_tokens 2048 > results/run_geox72b_std_prims_task.log 2>&1
kill $S
echo Q72BSTD_DONE >> results/queue_72b.log
