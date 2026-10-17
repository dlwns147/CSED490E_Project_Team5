#!/bin/bash
# X1-Q36R (docs/prereg/PREREG_X1.md): Qwen3.6 thinking on MATH-500 + AIME with the model card's sampling, 80k cap; GPU1; resumable, 4 attempts.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_TIMEOUT=14400 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5
for att in 1 2 3 4; do
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8065 1 0.88 x1q36r_$att --max-num-seqs 64 --language-model-only --max-model-len 90000) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8065/v1
  for sd in 1 2 3; do $P poc/run_math.py q36c think $sd --think --max_tokens 80000 >> results/x1/run_q36c_think_s$sd.log 2>&1 & done; wait
  kill $S; sleep 20
  n=$(cat results/x1/math_q36c_think_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 1680 ] && break
done
echo "S2_X1Q36R done ($n/1680 rows) $(date)" >> results/queue_log.txt
X1_THINK_TAG=q36c timeout 3600 $P poc/analyze_x1.py q36 > results/x1/analysis_q36c.log 2>&1
echo "S2_X1Q36R analysis -> results/x1/analysis_q36c.log $(date)" >> results/queue_log.txt
