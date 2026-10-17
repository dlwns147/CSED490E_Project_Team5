#!/bin/bash
# Does the distractor effect generalise to NL->solver? zebra code+snippet+status (no think) + K = 0/4/8 correct-but-unneeded CP-SAT API lines;
# 14B and 32B, T=0.7, 2 seeds
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do for k in 0 4 8; do
    $P poc/run_zebra.py --model_tag z${m}_docst_x${k}_t07s$sd --arms code --api_doc --doc_status --doc_extra $k --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_zebra_z${m}_docst_x${k}_t07s$sd.log 2>&1
  done; done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-14B 8068 q14b_zdis 14b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8069 q32b_zdis 32b & L2=$!
wait $L1 $L2
echo ZDIS_DONE >> results/queue_zebra.log
