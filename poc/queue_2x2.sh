#!/bin/bash
# 2x2 rewriter x solver on newer problems: Llama-3.1-8B as SOLVER on Qwen-written vs Llama-written story rewrites
# (Qwen-solver arms already exist). Self-paraphrase effect = each solver does better on its own rewrites?
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
poc/serve_cpu.sh Llama-3.1-8B-Instruct-Q4_K_M.gguf 8091 16 > results/server_llama_solver.log 2>&1 &
RPID=$!
until curl -sf localhost:8091/health >/dev/null; do sleep 2; done
export POC_BASE_URL=http://127.0.0.1:8091/v1
# Qwen-written rewrites (missing ones are written by Qwen on :8080, never by the solver)
$P poc/run_perturb.py --model_tag rwQ_solL_eval --source eval --exclude_multi --n_items 95 --k 2 --versions orig,story \
   --rewriter_url http://127.0.0.1:8080/v1 --workers 16 > results/run_rwQ_solL.log 2>&1
$P poc/run_perturb.py --model_tag rwL_solL_eval --source eval --exclude_multi --n_items 95 --k 2 --versions orig,story \
   --rewriter_url http://127.0.0.1:8091/v1 --rw_suffix _llama --workers 16 > results/run_rwL_solL.log 2>&1
kill $RPID
echo TWOBYTWO_DONE >> results/run_rwL_solL.log
