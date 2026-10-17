#!/bin/bash
# CO distractor dose-response: scoped snippet + K = 0/4/8 correct-but-unneeded CP-SAT API lines; solver arm + 2 repairs, n_inst 6 (84), T=0.7, 2 seeds
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do for k in 0 4 8; do
    $P poc/run_co.py --model_tag D_co${m}_x${k}_s$sd --arms solver --api_doc_task --doc_extra $k --repair 2 --temperature 0.7 --seed $sd > results/run_D_co${m}_x${k}_s$sd.log 2>&1
  done; done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8053 q8b_codis 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8054 q14b_codis 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8055 q32b_codis 32b & L3=$!
wait $L1 $L2 $L3
echo CODIS_DONE >> results/queue_coseeds.log
