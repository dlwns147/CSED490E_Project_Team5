#!/bin/bash
# Smoke test of the Slurm setup (2026-10-22; run through poc/slurm/job.sh): 10 OptiBench problems with the solver-choice prompt
# (free, seed 1) for each 24 GB model, to compare accuracy and tokens with the old server's runs (docs/prereg/PREREG_HO.md, OB).
# Also installs Qwen3-14B-AWQ into the shared model pool (downloaded to $POC_DATA/stage on the login node; the pool is root-owned).
echo "versions: $(/opt/conda/bin/python -c 'import vllm, torch; print("vllm", vllm.__version__, "torch", torch.__version__)' 2>&1 | tail -1); $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
if [ ! -f /SSD/huggingface/Qwen/Qwen3-14B-AWQ/model-00002-of-00002.safetensors ]; then
  cp -r $POC_DATA/stage/Qwen3-14B-AWQ /SSD/huggingface/Qwen/ && chown -R root:root /SSD/huggingface/Qwen/Qwen3-14B-AWQ && echo "installed Qwen3-14B-AWQ"
fi
export NLOPT_SET=optibench NLOPT_LIMIT=10 POC_BASE_URL=http://127.0.0.1:$PORT/v1
for spec in "Qwen/Qwen3-8B q8b" "Qwen/Qwen3-14B-AWQ q14a" "openai/gpt-oss-20b oss20 low"; do
  set -- $spec; dir=$1 m=$2
  t0=$(date +%s)
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 0.92 slurm_smoke_$m --max-model-len 20480) || { echo "$m: server failed"; tail -5 results/server_vllm_slurm_smoke_$m.log; continue; }
  echo "$m: server up in $(( $(date +%s) - t0 )) s"
  t0=$(date +%s)
  POC_REASONING_EFFORT=$3 $P poc/run_nlopt.py slurm_smoke_${m}_optibench free 1 --max_tokens 8192
  echo "$m: 10 problems in $(( $(date +%s) - t0 )) s; $(grep -m1 -oE 'Avg generation throughput: [0-9.]+ tokens/s' results/server_vllm_slurm_smoke_$m.log | tail -1)"
  kill $S; sleep 15
done
