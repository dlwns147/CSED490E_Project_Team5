#!/bin/bash
# checker v2 (fixed prompt + harness) -> code/blind/placebo on 128 items -> 1.7B scaling
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
$P poc/run_checker.py --model_tag qwen3-8b --n_items 60 --k 2 --workers 16 > results/run_checker_qwen3-8b.log 2>&1
echo CHECKER_DONE >> results/run_checker_qwen3-8b.log
$P poc/run_hack.py --model_tag qwen3-8b --n_items 128 --k 2 --workers 16 --strategies stress,stress_blind,stress_placebo > results/run_hack_big_qwen3-8b.log 2>&1
echo BIG_DONE >> results/run_hack_big_qwen3-8b.log
nohup poc/serve_cpu.sh Qwen3-1.7B-Q8_0.gguf 8081 16 > results/server_1.7b.log 2>&1 &
until curl -sf localhost:8081/health >/dev/null; do sleep 2; done
export POC_BASE_URL=http://127.0.0.1:8081/v1
$P poc/run_hack.py --model_tag qwen3-1.7b --n_items 40 --k 2 --workers 16 --strategies blind,direct,bugfirst,stress_blind,stress > results/run_hack_qwen3-1.7b.log 2>&1
$P poc/run_exec.py --model_tag qwen3-1.7b > results/run_exec_qwen3-1.7b.log 2>&1
echo SCALE_DONE >> results/run_exec_qwen3-1.7b.log
