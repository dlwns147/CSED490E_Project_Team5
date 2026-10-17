#!/bin/bash
# X1 for optimization (8B, scoped snippet, repair 2): budget-forced thinking B=256/1024/2048 on the main 4 problems (84 inst) and the
# held-out binpack/vcover (108 inst), token-accounted; compared offline with single / best-of-3 (label-free objective selection) and full thinking.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8078 q8b_cobud); export POC_BASE_URL=http://127.0.0.1:8078/v1
for B in 256 1024 2048; do
  $P poc/run_co.py --model_tag B_co8b_doctask_b$B --arms solver --api_doc_task --repair 2 --temperature 0.7 --seed 1 --think_budget $B > results/run_B_co8b_b$B.log 2>&1
  $P poc/run_co.py --model_tag B_coH8b_doctask_b$B --arms solver --api_doc_task --repair 2 --probs binpack,vcover --n_inst 18 --temperature 0.7 --seed 1 --think_budget $B > results/run_B_coH8b_b$B.log 2>&1
done
kill $S
echo COBUDGET_DONE >> results/queue_log.txt
