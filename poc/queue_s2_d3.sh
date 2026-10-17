#!/bin/bash
# D3 (PREREG_D1.md): hinted self-solutions on base Qwen3-8B (8040 GPU0), train D3 (GPU1), evaluate (8041 GPU1).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B 8040 0 0.85 d3_base) || exit 1
POC_BASE_URL=http://127.0.0.1:8040/v1 $P poc/d3_hint.py > results/h2/d3_hint.log 2>&1; kill $S
CUDA_VISIBLE_DEVICES=1 E4_DATA=results/h2/d3_D3.jsonl /opt/conda/bin/python poc/sft_lora.py /dev/shm/e4_d3 mixed 10000 2 > results/h2/d3_train.log 2>&1
S1=$(bash poc/start_server.sh /dev/shm/e4_d3 8041 1 0.85 d3_eval) || exit 1
for sd in 1 2 3; do POC_BASE_URL=http://127.0.0.1:8041/v1 $P poc/run_cc.py run q8b_d3 $sd > results/h2/run_full_q8b_d3_s$sd.log 2>&1 & done; wait
kill $S1
echo "S2_D3 runs done $(date)" >> results/queue_log.txt
