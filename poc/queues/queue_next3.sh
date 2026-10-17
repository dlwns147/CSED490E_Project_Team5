#!/bin/bash
# after the big PoC #1 run: (a) tighten the key noisy contrast stress vs stress_blind on all 128 items (8B),
# (b) model-size scaling: Qwen3-1.7B on PoC #2 (40 items, all strategies) and PoC #5, served on :8081
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
until grep -q QUEUE2_DONE results/run_perturb_train_qwen3-8b.log 2>/dev/null; do sleep 30; done
$P poc/run_hack.py --model_tag qwen3-8b --n_items 128 --k 2 --workers 16 --strategies stress,stress_blind > results/run_hack_big_qwen3-8b.log 2>&1
echo BIG_DONE >> results/run_hack_big_qwen3-8b.log
nohup poc/serve_cpu.sh Qwen3-1.7B-Q8_0.gguf 8081 16 > results/server_1.7b.log 2>&1 &
until curl -sf localhost:8081/health >/dev/null; do sleep 2; done
export POC_BASE_URL=http://127.0.0.1:8081/v1
$P poc/run_hack.py --model_tag qwen3-1.7b --n_items 40 --k 2 --workers 16 --strategies blind,direct,bugfirst,stress_blind,stress > results/run_hack_qwen3-1.7b.log 2>&1
$P poc/run_exec.py --model_tag qwen3-1.7b > results/run_exec_qwen3-1.7b.log 2>&1
echo SCALE_DONE >> results/run_exec_qwen3-1.7b.log
