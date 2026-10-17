#!/bin/bash
# 32B resumed with a bigger KV budget (GPU 0, frac 0.70 -> leaves >=24 GB for the foreign job) and a 64-item thinking run
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
echo "qwen3-32b: GPU 3 frac 0.70 ($(date))" >> results/gpu_choice.log
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8000 3 0.70 > results/server_vllm_qwen3-32b.log 2>&1 &
SPID=$!
until curl -sf localhost:8000/health >/dev/null; do sleep 5; kill -0 $SPID 2>/dev/null || { echo "vLLM died"; exit 1; }; done
export POC_BASE_URL=http://127.0.0.1:8000/v1
( POC_VERIFY_THREADS=24 $P poc/run_hack.py --model_tag v32b_think --n_items 64 --k 2 --workers 24 --think --max_tokens 12000 \
    --strategies stress,stress_blind,stress_placebo > results/run_v32b_think.log 2>&1; echo THINK_DONE >> results/run_v32b_think.log ) &
( while pgrep -f "run_checker2.py --model_tag v32b_nothink" >/dev/null; do sleep 60; done
  $P poc/checker_policies.py v32b_nothink > results/checker_policies_v32b_nothink.log 2>&1
  $P poc/run_checker2.py --model_tag v32b_think --k 4 --workers 24 --think --max_tokens 12000 > results/run_checker2_v32b_think.log 2>&1
  $P poc/checker_policies.py v32b_think > results/checker_policies_v32b_think.log 2>&1 ) &
wait
kill $SPID
echo GPU2_DONE >> results/queue_gpu2c.log
