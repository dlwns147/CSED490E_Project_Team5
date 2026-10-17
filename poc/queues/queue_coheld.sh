#!/bin/bash
# HELD-OUT CO problems (bin packing, min vertex cover; designed after all CO findings): solver arm + 2 repairs x {no doc, full sheet, scoped snippet},
# 2 seeds, + direct arm 1 seed; n_inst 18 (108 instances), T=0.7. References precomputed (all proven optimal).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--probs binpack,vcover --n_inst 18 --temperature 0.7"
  $P poc/run_co.py --model_tag H_co${m}_direct_s1 --arms direct $X --seed 1 > results/run_H_co${m}_direct_s1.log 2>&1
  for sd in 1 2; do for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do n=${v%%:*}; x=${v#*:}
    $P poc/run_co.py --model_tag H_co${m}_${n}_s$sd --arms solver $x --repair 2 $X --seed $sd > results/run_H_co${m}_${n}_s$sd.log 2>&1
  done; done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8062 q8b_coh 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8063 q14b_coh 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8064 q32b_coh 32b & L3=$!
wait $L1 $L2 $L3
echo COHELD_DONE >> results/queue_coseeds.log
