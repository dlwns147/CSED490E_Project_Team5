#!/bin/bash
# runs after the exec PoC: stress_blind control for PoC #2 on the same 40 items
cd /NAS/SJ/POSTECH/nlp
until grep -q EXEC_DONE results/run_exec_qwen3-8b.log 2>/dev/null; do sleep 30; done
/root/venvs/llm_algo_poc/bin/python poc/run_hack.py --model_tag qwen3-8b --n_items 40 --k 2 --workers 16 --strategies stress_blind > results/run_hack_ctrl_qwen3-8b.log 2>&1
echo CTRL_DONE >> results/run_hack_ctrl_qwen3-8b.log
