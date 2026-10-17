#!/bin/bash
# E5c: does task DIVERSITY give transfer? (4-task leave-one-out did not.)
# Step 1: thinking-teacher data for the other 5 geometry tasks (convex, tri, overlap, lattice, rectunion), training instances, K 0/4/8.
# Step 2: 10-task leave-one-out for targets hull / convex / tri: train mixed LoRA on the other 9 tasks (600 examples, same size as before,
#         so fewer per task), eval the target with K0 and K8, seeds 1-2 (base for these sets exists: E5_geoxbase_main/held_k*, seeds 1-2).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
gen() { S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $1 $2 0.45 q8b_e5cgen_k$3) || { echo "e5c gen k$3 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$1/v1
  $P poc/run_geo_cross.py --model_tag T_geox8b_train2_k$3_think --tasks convex,tri,overlap,lattice,rectunion --inst_prefix train- --save_prompt \
     --stdlib --n_inst 60 --distract $3 --think --max_tokens 16000 --temperature 0.7 --seed 1 > results/run_T_geox8b_train2_k$3.log 2>&1
  kill $S; }
gen 8053 0 0 & A=$!
sleep 30
gen 8054 1 8 & B=$!
sleep 30
gen 8055 3 4 & C=$!
wait $A $B $C
echo E5CGEN_DONE >> results/queue_log.txt
one() { t=$1; g=$2; port=$3
  ( cd /dev/shm && E5_EXTRA="T_geox8b_train2_k{k}_think" CUDA_VISIBLE_DEVICES=$g PYTHONPATH=/dev/shm/pylib_vllm /opt/conda/bin/python /NAS/SJ/POSTECH/nlp/poc/sft_lora.py /dev/shm/e5c_loto_$t mixed 600 2 $t ) > results/e5c_train_loto_$t.log 2>&1
  S=$(poc/start_server.sh /dev/shm/e5c_loto_$t $port $g 0.45 e5cloto_$t) || { echo "e5cloto $t failed" >> results/queue_log.txt; rm -rf /dev/shm/e5c_loto_$t; return; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  for k in 0 8; do for sd in 1 2; do
    $P poc/run_geo_cross.py --model_tag E5C_geox_${t}_k${k}_s$sd --tasks $t --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed $sd --distract $k > results/run_E5C_${t}_k${k}_s$sd.log 2>&1
  done; done
  kill $S; sleep 15; rm -rf /dev/shm/e5c_loto_$t; }
one hull 0 8053 & A=$!
one convex 1 8054 & B=$!
one tri 3 8055 & C=$!
wait $A $B $C
echo E5C_DONE >> results/queue_log.txt
