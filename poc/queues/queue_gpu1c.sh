#!/bin/bash
# parallel lanes on the same vLLM server (GPU was idle ~97% of the time while the CPU verified)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8000/v1
( POC_VERIFY_THREADS=24 $P poc/run_hack.py --model_tag v8b_think --n_items 128 --k 2 --workers 64 --think --max_tokens 14000 \
    --strategies stress,stress_blind,stress_placebo > results/run_v8b_think.log 2>&1; echo THINK_DONE >> results/run_v8b_think.log ) &
( $P poc/run_checker2.py --model_tag v8b_nothink --k 4 --workers 64 > results/run_checker2_v8b_nothink.log 2>&1
  $P poc/run_checker2.py --model_tag v8b_think --k 4 --workers 64 --think --max_tokens 14000 > results/run_checker2_v8b_think.log 2>&1
  echo CHK_DONE >> results/run_checker2_v8b_think.log ) &
wait
echo GPU1_DONE >> results/queue_gpu1c.log
