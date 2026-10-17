#!/bin/bash
# D1 (docs/prereg/PREREG_D1.md): train Qwen3-8B LoRA arms A (GPU1) and B (GPU3); base Qwen3-8B on GPU0 (8040); then evaluate A / B.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
( CUDA_VISIBLE_DEVICES=1 E4_DATA=results/h2/d1_train_A.jsonl /opt/conda/bin/python poc/sft_lora.py /dev/shm/e4_d1A mixed 10000 2 > results/h2/d1_train_A.log 2>&1 ) &
TA=$!
( CUDA_VISIBLE_DEVICES=3 E4_DATA=results/h2/d1_train_A.jsonl E4_REPLAY=results/e4_replay_B_self.jsonl /opt/conda/bin/python poc/sft_lora.py /dev/shm/e4_d1B mixed 10000 2 > results/h2/d1_train_B.log 2>&1 ) &
TB=$!
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8040 0 0.85 d1_base) || exit 1
  for sd in 1 2 3; do POC_BASE_URL=http://127.0.0.1:8040/v1 $P poc/run_cc.py run q8b_plain $sd > results/h2/run_full_q8b_plain_s$sd.log 2>&1 & done; wait
  kill $S ) &
ev() { arm=$1 port=$2 gpu=$3
  S=$(bash poc/start_server.sh /dev/shm/e4_$arm $port $gpu 0.85 d1_$arm) || { echo "d1 $arm server failed $(date)" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  for sd in 1 2 3; do $P poc/run_cc.py run q8b_$arm $sd > results/h2/run_full_q8b_${arm}_s$sd.log 2>&1 & done
  X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
  r() { tag=S2_E4_${arm}_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1; }
  for k in 0 8; do for sd in 1 2; do r hull_k${k}_s$sd --tasks hull --seed $sd --distract $k & done; done
  r diam_s1 --tasks diameter --seed 1 & r delfixed_s1 --tasks delaunay --seed 1 --distract 0 --incircle fixed &
  wait; kill $S; }
( wait $TA 2>/dev/null; while kill -0 $TA 2>/dev/null; do sleep 30; done; ev d1A 8041 1 ) &
( while kill -0 $TB 2>/dev/null; do sleep 30; done; ev d1B 8043 3 ) &
wait
echo "S2_D1 runs done $(date)" >> results/queue_log.txt
