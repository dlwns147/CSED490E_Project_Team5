#!/bin/bash
# D2 (PREREG_D1.md): Qwen3-8B seeds 4-8 on 8040 (GPU0) and 8042 (GPU2); build S / L data; train S (GPU1), L (GPU3); evaluate.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
S0=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8040 0 0.85 d2_base0) || exit 1
S2=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8042 2 0.85 d2_base2) || exit 1
for sd in 4 5 6; do POC_BASE_URL=http://127.0.0.1:8040/v1 $P poc/run_cc.py run q8b_plain $sd > results/h2/run_full_q8b_plain_s$sd.log 2>&1 & done
for sd in 7 8; do POC_BASE_URL=http://127.0.0.1:8042/v1 $P poc/run_cc.py run q8b_plain $sd > results/h2/run_full_q8b_plain_s$sd.log 2>&1 & done
wait; kill $S0 $S2
$P poc/d2_data.py > results/h2/d2_data.log 2>&1
tr() { arm=$1 gpu=$2 port=$3
  CUDA_VISIBLE_DEVICES=$gpu E4_DATA=results/h2/d2_$arm.jsonl /opt/conda/bin/python poc/sft_lora.py /dev/shm/e4_d2$arm mixed 10000 2 > results/h2/d2_train_$arm.log 2>&1
  S=$(bash poc/start_server.sh /dev/shm/e4_d2$arm $port $gpu 0.85 d2_$arm) || return
  for sd in 1 2 3; do POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run q8b_d2$arm $sd > results/h2/run_full_q8b_d2${arm}_s$sd.log 2>&1 & done; wait; kill $S; }
tr S 1 8041 & tr L 3 8043 & wait
echo "S2_D2 runs done $(date)" >> results/queue_log.txt
