#!/bin/bash
# usage: serve_gpu.sh <hf-model-dir> <port> <gpu-id> <mem-fraction> [extra vllm args...]   (OpenAI API at :port/v1)
# Server 2 (from 2026-10-13, RTX PRO 6000 Blackwell): vLLM 0.22 (torch 2.11 cu130) in the base conda python (/opt/conda).
# Old server: vLLM 0.10.2 as a --target dir in /dev/shm/pylib_vllm (set POC_PYLIB to use such a dir again).
# GPUs are SHARED with other containers: pin one GPU and cap the memory fraction to what is actually free.
[ -n "$POC_PYLIB" ] && export PYTHONPATH=$POC_PYLIB
export CUDA_VISIBLE_DEVICES=$3
export HF_HOME=${HF_HOME:-/dev/shm/hf_home_poc} VLLM_CACHE_ROOT=${VLLM_CACHE_ROOT:-/dev/shm/vllm_cache_poc}   # Slurm: poc/slurm/job.sh sets both
export VLLM_USE_FLASHINFER_SAMPLER=0   # Blackwell + vLLM 0.22: engine init fails ("FlashInfer requires sm75") without it
cd /dev/shm   # cwd on the NAS made every import probe CIFS first (python puts cwd on sys.path)
exec ${POC_VLLM_PY:-/opt/conda/bin/python} -m vllm.entrypoints.openai.api_server --model $1 --served-model-name local \
  --host 127.0.0.1 --port $2 --gpu-memory-utilization $4 --max-model-len 32768 --enable-prefix-caching "${@:5}"
