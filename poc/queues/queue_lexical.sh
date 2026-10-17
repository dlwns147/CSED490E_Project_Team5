#!/bin/bash
# E3 retrieval baseline for tool scoping: top-1 helper by IDF-weighted word overlap (task text vs helper name+doc) from the K=8 pool;
# n=100, T=0.7, seeds 1-2 (same settings as the auto8 self-scoping runs: pick 80/83.5/85, dis8 74.5/75/75.5, oracle 98/84.5/95.5). No --stdlib, to match.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
for spec in "Qwen3-8B:8b:8077" "Qwen3-14B:14b:8078" "Qwen3-32B-AWQ:32b:8079"; do
  IFS=: read mdl m port <<< "$spec"
  S=$(start /SSD/huggingface/Qwen/$mdl $port q${m}_lex); export POC_BASE_URL=http://127.0.0.1:$port/v1
  for sd in 1 2; do $P poc/run_geo_cross.py --model_tag geox${m}_auto8lexical_t07s$sd --distract 8 --autoscope --autoscope_mode lexical --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_auto8lexical_s$sd.log 2>&1; done
  kill $S; sleep 20
done
echo LEXICAL_DONE >> results/queue_log.txt
