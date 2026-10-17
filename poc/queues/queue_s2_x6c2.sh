#!/bin/bash
# X6 addendum 2, resumed (docs/prereg/PREREG_X3.md): Qwen3.6 think / thinkf with the model card's sampling, 80k cap, on GPU2 with vLLM's
# V2 model runner (VLLM_USE_V2_MODEL_RUNNER=1 keeps the presence-penalty state on the GPU; the V1 runner rebuilt it on the CPU every
# step: 0.6-1.1k tok/s). Same tag q36c, resumes the 423 rows written before the pause. Usage: bash queue_s2_x6c2.sh <server PID already on 8066>
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_TIMEOUT=14400 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5 VLLM_USE_V2_MODEL_RUNNER=1
S=$1
for att in 1 2 3 4; do
  [ -z "$S" ] && { S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8066 2 0.88 x6c2_$att --max-num-seqs 64 --language-model-only --max-model-len 90000) || { S=""; sleep 60; continue; }; }
  export POC_BASE_URL=http://127.0.0.1:8066/v1
  for md in think thinkf; do for sd in 1 2 3; do $P poc/run_nlopt.py q36c $md $sd --think --max_tokens 80000 >> results/x3/run_q36c_${md}_s$sd.log 2>&1 & done; done; wait
  kill $S; sleep 20; S=""
  n=$(cat results/x3/opt_q36c_think_s*.jsonl results/x3/opt_q36c_thinkf_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 2070 ] && break
done
echo "S2_X6c q36c done ($n/2070 rows, V2 runner) $(date)" >> results/queue_log.txt
