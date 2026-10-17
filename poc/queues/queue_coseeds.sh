#!/bin/bash
# CO headline under sampling: solver arm (repair 2) x {no doc, full sheet, scoped snippet} x 3 seeds (T=0.7), 8B and 14B
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1
  for sd in 1 2 3; do
    for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do
      n=${v%%:*}; x=${v#*:}
      $P poc/run_co.py --model_tag co$4_${n}_t07s$sd --arms solver $x --repair 2 --temperature 0.7 --seed $sd > results/run_co$4_${n}_t07s$sd.log 2>&1
    done
  done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8058 q8b_coseeds 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8059 q14b_coseeds 14b & L2=$!
wait $L1 $L2
echo COSEEDS_DONE >> results/queue_coseeds.log
