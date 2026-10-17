#!/bin/bash
# Final, powered CO table: n_inst=18 (252 instances), solver arm + 2 repairs, T=0.7, 3 seeds x {no doc, full sheet, scoped snippet}; 8B / 14B / 32B.
# References precomputed (co_refs.json is rewritten only when new keys appear).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2 3; do for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do n=${v%%:*}; x=${v#*:}
    $P poc/run_co.py --model_tag F_co${m}_${n}_s$sd --arms solver $x --repair 2 --n_inst 18 --temperature 0.7 --seed $sd > results/run_F_co${m}_${n}_s$sd.log 2>&1
  done; done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8050 q8b_fco 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8051 q14b_fco 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8052 q32b_fco 32b & L3=$!
wait $L1 $L2 $L3
echo FINALCO_DONE >> results/queue_coseeds.log
