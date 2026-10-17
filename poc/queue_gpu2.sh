#!/bin/bash
# GPU queue 2: scale — Qwen3-32B-AWQ on PoC #2 (no-think + think; target / placebo / blind) and PoC #6 checkers + policies
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
SPID=$(poc/start_vllm.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ qwen3-32b) || { echo "vLLM could not start"; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8000/v1
( POC_VERIFY_THREADS=24 $P poc/run_hack.py --model_tag v32b_nothink --n_items 128 --k 2 --workers 64 --strategies stress,stress_blind,stress_placebo > results/run_v32b_nothink.log 2>&1
  POC_VERIFY_THREADS=24 $P poc/run_hack.py --model_tag v32b_think --n_items 128 --k 2 --workers 64 --think --max_tokens 14000 --strategies stress,stress_blind,stress_placebo > results/run_v32b_think.log 2>&1 ) &
( $P poc/run_checker2.py --model_tag v32b_nothink --k 4 --workers 64 > results/run_checker2_v32b_nothink.log 2>&1
  $P poc/checker_policies.py v32b_nothink > results/checker_policies_v32b_nothink.log 2>&1
  $P poc/run_checker2.py --model_tag v32b_think --k 4 --workers 64 --think --max_tokens 14000 > results/run_checker2_v32b_think.log 2>&1
  $P poc/checker_policies.py v32b_think > results/checker_policies_v32b_think.log 2>&1 ) &
wait
kill $SPID
echo GPU2_DONE >> results/queue_gpu2.log
