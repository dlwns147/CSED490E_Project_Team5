#!/bin/bash
# GPU queue 1 (GPU 2 only): Qwen3-8B bf16 — #2 thinking-mode placebo test, then #6b checkers (non-think + think)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
read GPU FRAC < <(poc/pick_gpu.sh) || { echo "no free GPU"; exit 1; }
echo "using GPU $GPU frac $FRAC" > results/gpu_choice.log
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen3-8B 8000 $GPU $FRAC > results/server_vllm_qwen3-8b.log 2>&1 &
SPID=$!
until curl -sf localhost:8000/health >/dev/null; do sleep 5; kill -0 $SPID 2>/dev/null || { echo "vLLM died"; exit 1; }; done
export POC_BASE_URL=http://127.0.0.1:8000/v1
$P poc/run_hack.py --model_tag v8b_nothink --n_items 128 --k 2 --workers 64 --strategies stress,stress_blind,stress_placebo > results/run_v8b_nothink.log 2>&1
$P poc/run_hack.py --model_tag v8b_think --n_items 128 --k 2 --workers 64 --think --max_tokens 14000 --strategies stress,stress_blind,stress_placebo > results/run_v8b_think.log 2>&1
$P poc/run_checker2.py --model_tag v8b_nothink --k 4 --workers 64 > results/run_checker2_v8b_nothink.log 2>&1
$P poc/run_checker2.py --model_tag v8b_think --k 4 --workers 64 --think --max_tokens 14000 > results/run_checker2_v8b_think.log 2>&1
echo GPU1_DONE >> results/run_checker2_v8b_think.log
