#!/bin/bash
# larger-n follow-up for the noisiest compression cell: solve rate, 95 unique-answer problems x k=2, Q8 vs Q4 vs Q3
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
until grep -q SCALE_DONE results/run_exec_qwen3-1.7b.log 2>/dev/null; do sleep 60; done
for c in "q8_0|Qwen3-8B-Q8_0.gguf" "q4km|Qwen3-8B-Q4_K_M.gguf" "q3km|Qwen3-8B-Q3_K_M.gguf"; do
  IFS='|' read -r tag model <<< "$c"
  log=results/solvebig_${tag}.log
  grep -q DONE $log 2>/dev/null && continue
  poc/serve_cpu.sh $model 8090 16 > results/server_solvebig_${tag}.log 2>&1 &
  SPID=$!
  until curl -sf localhost:8090/health >/dev/null; do sleep 2; done
  POC_BASE_URL=http://127.0.0.1:8090/v1 $P poc/run_perturb.py --model_tag s95_${tag} --source train --exclude_multi \
      --n_items 95 --k 2 --versions orig --workers 16 >> $log 2>&1
  kill $SPID; wait $SPID 2>/dev/null; sleep 3
  echo DONE >> $log
done
echo SOLVEBIG_DONE >> results/solvebig_all.log
