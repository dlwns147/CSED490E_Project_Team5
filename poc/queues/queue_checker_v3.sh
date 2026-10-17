#!/bin/bash
# re-evaluate the (already generated) checkers with per-batch timeouts; runs alongside the big hack run (sandbox only)
cd /NAS/SJ/POSTECH/nlp
until grep -q CHECKER_DONE results/run_checker_qwen3-8b.log 2>/dev/null; do sleep 20; done
cp results/run_checker_qwen3-8b.log results/archive/v2_run_checker_qwen3-8b.log
cp results/checker_verdicts_qwen3-8b.json results/archive/v2_checker_verdicts_qwen3-8b.json
/root/venvs/llm_algo_poc/bin/python poc/run_checker.py --model_tag qwen3-8b --n_items 60 --k 2 > results/run_checker_v3_qwen3-8b.log 2>&1
echo CHECKER_V3_DONE >> results/run_checker_v3_qwen3-8b.log
