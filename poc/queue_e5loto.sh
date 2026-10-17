#!/bin/bash
# E5b leave-one-task-out: does the learned robustness transfer to an UNSEEN task? For each core task t, train the mixed LoRA (K0/K4/K8 thirds,
# 600 examples, 2 epochs) on the other 4 tasks, then eval on t only (no thinking, T=0.7, seeds 1-2, K0 and K8: 120 programs each).
# Merged models live in /dev/shm and are deleted after their eval. GPUs 0 / 1 / 3 in parallel (hull+area2 / pip+segs / close).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
one() { t=$1; g=$2; port=$3
  ( cd /dev/shm && CUDA_VISIBLE_DEVICES=$g PYTHONPATH=/dev/shm/pylib_vllm /opt/conda/bin/python /NAS/SJ/POSTECH/nlp/poc/sft_lora.py /dev/shm/e5_loto_$t mixed 600 2 $t ) > results/e5_train_loto_$t.log 2>&1
  S=$(poc/start_server.sh /dev/shm/e5_loto_$t $port $g 0.45 e5loto_$t) || { echo "e5loto $t failed" >> results/queue_log.txt; rm -rf /dev/shm/e5_loto_$t; return; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  for k in 0 8; do for sd in 1 2; do
    $P poc/run_geo_cross.py --model_tag E5L_geox_${t}_k${k}_s$sd --tasks $t --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed $sd --distract $k > results/run_E5L_${t}_k${k}_s$sd.log 2>&1
  done; done
  kill $S; sleep 15; rm -rf /dev/shm/e5_loto_$t; }
( one hull 0 8046; one area2 0 8046 ) & A=$!
( one pip 1 8047; one segs 1 8047 ) & B=$!
( one close 3 8048 ) & C=$!
# base model, seed 2 for the same eval sets (seed 1 = E5_geoxbase_main_k*) on GPU 3 after close
wait $C
S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8048 3 0.45 e5base_s2) && { export POC_BASE_URL=http://127.0.0.1:8048/v1
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag E5_geoxbase_main_k${k}_s2 --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 2 --distract $k > results/run_E5_base_main_k${k}_s2.log 2>&1; done
  kill $S; }
wait $A $B
echo E5LOTO_DONE >> results/queue_log.txt
