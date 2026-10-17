#!/bin/bash
# D1b' (PREREG_D1.md): rewrite on base Qwen3-8B (8040, GPU0); train E (GPU1) and D (GPU3); evaluate each on its GPU (test split via full run).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8040 0 0.85 d1b_base) || exit 1
( CUDA_VISIBLE_DEVICES=3 E4_DATA=results/h2/d1b_D.jsonl /opt/conda/bin/python poc/sft_lora.py /dev/shm/e4_d1D mixed 10000 2 > results/h2/d1b_train_D.log 2>&1
  S2=$(bash poc/start_server.sh /dev/shm/e4_d1D 8043 3 0.85 d1_d1D) && { for sd in 1 2 3; do POC_BASE_URL=http://127.0.0.1:8043/v1 $P poc/run_cc.py run q8b_d1D $sd > results/h2/run_full_q8b_d1D_s$sd.log 2>&1 & done; wait; kill $S2; } ) &
( POC_BASE_URL=http://127.0.0.1:8040/v1 $P poc/d1_rewrite.py > results/h2/d1b_rewrite.log 2>&1; kill $S
  CUDA_VISIBLE_DEVICES=1 E4_DATA=results/h2/d1b_E.jsonl /opt/conda/bin/python poc/sft_lora.py /dev/shm/e4_d1E mixed 10000 2 > results/h2/d1b_train_E.log 2>&1
  S1=$(bash poc/start_server.sh /dev/shm/e4_d1E 8041 1 0.85 d1_d1E) && { for sd in 1 2 3; do POC_BASE_URL=http://127.0.0.1:8041/v1 $P poc/run_cc.py run q8b_d1E $sd > results/h2/run_full_q8b_d1E_s$sd.log 2>&1 & done; wait; kill $S1; } ) &
wait
echo "S2_D1b runs done $(date)" >> results/queue_log.txt
