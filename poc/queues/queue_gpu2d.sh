#!/bin/bash
# controller for the rest of the 32B work on the running server (:8000, GPU 3)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8000/v1
while pgrep -f "checker_policies.py v32b_nothink" >/dev/null; do sleep 60; done
$P poc/run_checker2.py --model_tag v32b_think --k 4 --workers 24 --think --max_tokens 12000 > results/run_checker2_v32b_think.log 2>&1
$P poc/checker_policies.py v32b_think > results/checker_policies_v32b_think.log 2>&1
$P poc/run_checker2.py --model_tag v32b_nothink --k 4 --workers 24 > results/run_checker2_v32b_nothink.log 2>&1   # redo: repair round died in a server restart
while pgrep -f "run_hack.py --model_tag v32b_think" >/dev/null; do sleep 60; done
S=$(ps -eo pid,args | awk '/vllm.entrypoints.openai.api_server/ && !/awk/ {print $1}'); kill $S
echo GPU2_DONE >> results/queue_gpu2d.log
