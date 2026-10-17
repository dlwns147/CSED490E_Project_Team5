#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
until grep -q QUEUE_DONE results/run_perturb_qwen3-8b.log 2>/dev/null; do sleep 30; done
/root/venvs/llm_algo_poc/bin/python poc/run_exec.py --model_tag qwen3-8b > results/run_exec_qwen3-8b.log 2>&1
echo EXEC_DONE >> results/run_exec_qwen3-8b.log
