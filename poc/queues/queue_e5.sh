#!/bin/bash
# E5 steps 2-3 (restructured 16:25 so idle GPUs start early):
#  GPU 3: eval base Qwen3-8B now;  GPU 0: train CLEAN LoRA now (K0 data is complete), then eval it;
#  GPU 1: after queue_e5gen.sh (K8 data) finishes, train MIXED LoRA (K0/K4/K8 thirds), then eval it.
# Eval (no thinking, T=0.7 s1): main 5 tasks K0 & K8 (n=300 each), held-out convex/tri/overlap K0 & K8, hard lattice/rectunion, CO snippet (84).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
train() { ( cd /dev/shm && CUDA_VISIBLE_DEVICES=$1 PYTHONPATH=/dev/shm/pylib_vllm /opt/conda/bin/python /NAS/SJ/POSTECH/nlp/poc/sft_lora.py /dev/shm/e5_$2 $2 600 2 ) > results/e5_train_$2.log 2>&1; echo E5TRAIN_$2_DONE >> results/queue_log.txt; }
evalm() { S=$(poc/start_server.sh $1 $2 $3 0.45 e5eval_$4) || { echo "e5eval $4 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  for k in 0 8; do
    $P poc/run_geo_cross.py --model_tag E5_geox${m}_main_k${k} $X --distract $k > results/run_E5_${m}_main_k$k.log 2>&1
    $P poc/run_geo_cross.py --model_tag E5_geox${m}_held_k${k} --tasks convex,tri,overlap $X --distract $k > results/run_E5_${m}_held_k$k.log 2>&1
  done
  $P poc/run_geo_cross.py --model_tag E5_geox${m}_hard $X --tasks lattice,rectunion > results/run_E5_${m}_hard.log 2>&1
  $P poc/run_co.py --model_tag E5_co${m}_doctask --arms solver --api_doc --api_doc_task --repair 2 --temperature 0.7 --seed 1 > results/run_E5_co${m}.log 2>&1
  kill $S; }
evalm /SSD/huggingface/Qwen/Qwen3-8B 8045 3 base & E3=$!
( train 0 clean; evalm /dev/shm/e5_clean 8044 0 clean ) & E2=$!
( while kill -0 550323 2>/dev/null; do sleep 60; done; train 1 mixed; evalm /dev/shm/e5_mixed 8043 1 mixed ) & E1=$!
wait $E1 $E2 $E3
echo E5_DONE >> results/queue_log.txt
