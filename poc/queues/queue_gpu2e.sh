#!/bin/bash
# 32B resumed on GPU 2 (GPU 3 got a foreign job); frac 0.65 leaves ~16 GB beside the 3 GB foreign process
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
echo "qwen3-32b: GPU 2 frac 0.65 ($(date))" >> results/gpu_choice.log
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8000 2 0.65 > results/server_vllm_qwen3-32b.log 2>&1 &
SPID=$!
until curl -sf localhost:8000/health >/dev/null; do sleep 5; kill -0 $SPID 2>/dev/null || { echo "vLLM died"; exit 1; }; done
export POC_BASE_URL=http://127.0.0.1:8000/v1
( POC_VERIFY_THREADS=24 $P poc/run_hack.py --model_tag v32b_think --n_items 64 --k 2 --workers 48 --think --max_tokens 12000 \
    --strategies stress,stress_blind,stress_placebo >> results/run_v32b_think2.log 2>&1 ) &
( $P poc/run_checker2.py --model_tag v32b_think --k 4 --workers 24 --think --max_tokens 12000 > results/run_checker2_v32b_think.log 2>&1
  $P poc/checker_policies.py v32b_think > results/checker_policies_v32b_think.log 2>&1
  $P poc/run_checker2.py --model_tag v32b_nothink --k 4 --workers 24 > results/run_checker2_v32b_nothink.log 2>&1 ) &
wait
kill $SPID
echo GPU2_DONE >> results/queue_gpu2e.log
