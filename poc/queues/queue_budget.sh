#!/bin/bash
# How much thinking is needed to resist plausible helpers? Budget forcing B = 0 / 256 / 1024 / 4096 thinking tokens, K=8 related helpers,
# n=100, --stdlib, T=0.7 s1; Qwen3 8B / 14B / 32B. Anchors: no-think K=8 ≈ 71–77, full thinking K=8 = 97–99.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
for spec in "Qwen3-8B:8b:8098" "Qwen3-14B:14b:8099" "Qwen3-32B-AWQ:32b:8098"; do
  IFS=: read mdl m port <<< "$spec"
  S=$(start /SSD/huggingface/Qwen/$mdl $port q${m}_budget); export POC_BASE_URL=http://127.0.0.1:$port/v1
  for B in 0 256 1024 4096; do
    $P poc/run_geo_cross.py --model_tag B_geox${m}_dis8_b$B --stdlib --distract 8 --think_budget $B --max_tokens 4096 --temperature 0.7 --seed 1 > results/run_B_geox${m}_dis8_b$B.log 2>&1
  done
  kill $S; sleep 20
done
echo BUDGET_DONE >> results/queue_log.txt
