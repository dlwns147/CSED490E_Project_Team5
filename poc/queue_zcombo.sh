#!/bin/bash
# Complementarity test: snippet+status AND sampling (k=5) on zebra, no think. Existing: 14B nothink_docst_t07s1-2, 32B docst_x0_t07s1-2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {  # lane <model> <port> <tag> <short> <tagstem> <seeds...>
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; stem=$5; shift 5
  for sd in "$@"; do
    $P poc/run_zebra.py --model_tag z${m}_${stem}_t07s$sd --arms code --api_doc --doc_status --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_zebra_z${m}_${stem}_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-14B 8083 q14b_zcombo 14b nothink_docst 3 4 5; lane /SSD/huggingface/Qwen/Qwen3-8B 8084 q8b_zcombo 8b nothink_docst 1 2 3 4 5 ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8085 q32b_zcombo 32b docst_x0 3 4 5 & L2=$!
wait $L1 $L2
echo ZCOMBO_DONE >> results/queue_zebra.log
