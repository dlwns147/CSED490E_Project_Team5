#!/bin/bash
# after the stress_blind control: bigger, cleaner PoC #1 (unique-answer easy CF problems from 3 train shards, fixed rewrite prompt)
cd /NAS/SJ/POSTECH/nlp
until grep -q CTRL_DONE results/run_hack_ctrl_qwen3-8b.log 2>/dev/null; do sleep 30; done
/root/venvs/llm_algo_poc/bin/python poc/run_perturb.py --model_tag qwen3-8b_train --source train --exclude_multi --n_items 95 --k 2 --workers 16 > results/run_perturb_train_qwen3-8b.log 2>&1
echo QUEUE2_DONE >> results/run_perturb_train_qwen3-8b.log
