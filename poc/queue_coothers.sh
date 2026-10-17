#!/bin/bash
# CO plausible-distractor test: scoped snippet + the other three problems' snippets (related CO modelling patterns); 84 instances x 2 seeds, T=0.7
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do $P poc/run_co.py --model_tag D_co${m}_others_s$sd --arms solver --api_doc_task --doc_others --repair 2 --temperature 0.7 --seed $sd > results/run_D_co${m}_others_s$sd.log 2>&1; done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8056 q8b_coo 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8057 q14b_coo 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8058 q32b_coo 32b & L3=$!
wait $L1 $L2 $L3
echo COOTHERS_DONE >> results/queue_coseeds.log
