#!/bin/bash
# PoC #1 control: rewriter != solver (Llama-3.1-8B rewrites, Qwen3-8B Q4_K_M solves), newer (eval) vs older (train)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
until [ -s /root/llm_algo_poc_tools/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf ] && ! pgrep -x llama-quantize >/dev/null; do sleep 30; done
poc/serve_cpu.sh Llama-3.1-8B-Instruct-Q4_K_M.gguf 8091 16 > results/server_llama_rw.log 2>&1 &
RPID=$!
until curl -sf localhost:8091/health >/dev/null; do sleep 2; done
for src in eval train; do
  $P poc/run_perturb.py --model_tag rwllama_${src} --source $src --exclude_multi --n_items 95 --k 2 \
     --versions orig,story --rewriter_url http://127.0.0.1:8091/v1 --rw_suffix _llama --workers 16 \
     > results/run_rwllama_${src}.log 2>&1
done
kill $RPID
echo RWCTRL_DONE >> results/run_rwllama_train.log
