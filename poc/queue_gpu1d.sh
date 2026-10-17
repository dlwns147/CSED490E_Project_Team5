#!/bin/bash
# resume GPU queue 1 on the freest GPU (moved off GPU 2 when a foreign job grew there)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
read GPU FRAC < <(poc/pick_gpu.sh) || { echo "no free GPU"; exit 1; }
echo "using GPU $GPU frac $FRAC ($(date))" >> results/gpu_choice.log
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen3-8B 8000 $GPU $FRAC > results/server_vllm_qwen3-8b.log 2>&1 &
SPID=$!
until curl -sf localhost:8000/health >/dev/null; do sleep 5; kill -0 $SPID 2>/dev/null || { echo "vLLM died"; exit 1; }; done
export POC_BASE_URL=http://127.0.0.1:8000/v1
( POC_VERIFY_THREADS=24 $P poc/run_hack.py --model_tag v8b_think --n_items 128 --k 2 --workers 64 --think --max_tokens 14000 \
    --strategies stress,stress_blind,stress_placebo >> results/run_v8b_think.log 2>&1; echo THINK_DONE >> results/run_v8b_think.log ) &
( $P poc/run_checker2.py --model_tag v8b_think --k 4 --workers 64 --think --max_tokens 14000 > results/run_checker2_v8b_think.log 2>&1
  $P poc/checker_policies.py v8b_think > results/checker_policies_v8b_think.log 2>&1; echo CHK_DONE >> results/run_checker2_v8b_think.log ) &
wait
echo GPU1_DONE >> results/queue_gpu1d.log
