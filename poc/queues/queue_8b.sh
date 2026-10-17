#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
$P poc/run_hack.py --model_tag qwen3-8b --n_items 40 --k 2 --workers 16 > results/run_hack_qwen3-8b.log 2>&1
$P poc/run_perturb.py --model_tag qwen3-8b --n_items 60 --k 2 --workers 16 > results/run_perturb_qwen3-8b.log 2>&1
echo QUEUE_DONE >> results/run_perturb_qwen3-8b.log
