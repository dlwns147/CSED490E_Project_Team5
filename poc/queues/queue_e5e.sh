#!/bin/bash
# E5e: is the damage to unseen tasks an over-training effect? 4-task leave-hull-out LoRA (same data as E5b) with lighter training:
#  A: r=16, lr 1e-4, 1 epoch (half the steps)   B: r=4, lr 5e-5, 1 epoch   C: r=16, lr 1e-4, 2 epochs, 150 examples (quarter data)
# Eval: hull K0 / K8 (unseen; E5b 2-epoch version: 34 / 21, base 97 / 15) and the 4 trained tasks under K8 (in-task gain), seed 1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
cfg() { name=$1; g=$2; port=$3; r=$4; lr=$5; n=$6; ep=$7
  ( cd /dev/shm && E5_R=$r E5_LR=$lr CUDA_VISIBLE_DEVICES=$g PYTHONPATH=/dev/shm/pylib_vllm /opt/conda/bin/python /NAS/SJ/POSTECH/nlp/poc/sft_lora.py /dev/shm/e5e_$name mixed $n $ep hull ) > results/e5e_train_$name.log 2>&1
  S=$(poc/start_server.sh /dev/shm/e5e_$name $port $g 0.45 e5e_$name) || { echo "e5e $name failed" >> results/queue_log.txt; rm -rf /dev/shm/e5e_$name; return; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag E5E_geox${name}_hull_k$k --tasks hull $X --distract $k > results/run_E5E_${name}_hull_k$k.log 2>&1; done
  $P poc/run_geo_cross.py --model_tag E5E_geox${name}_other_k8 --tasks area2,pip,segs,close $X --distract 8 > results/run_E5E_${name}_other_k8.log 2>&1
  kill $S; sleep 15; rm -rf /dev/shm/e5e_$name; }
cfg A 0 8058 16 1e-4 600 1 & A=$!
cfg B 1 8059 4 5e-5 600 1 & B=$!
cfg C 3 8060 16 1e-4 150 2 & C=$!
wait $A $B $C
echo E5E_DONE >> results/queue_log.txt
