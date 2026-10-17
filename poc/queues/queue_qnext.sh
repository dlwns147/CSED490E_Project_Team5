#!/bin/bash
# E1 (architecture variety): Qwen3-Next-80B-A3B-Instruct (hybrid-attention MoE, AWQ 4-bit, 46 GB → one GPU at 0.75). Same arms as the cross-family runs.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
while true; do G=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 5000 {print $1; exit}'); [ -n "$G" ] && break; sleep 120; done
S=$(poc/start_server.sh /SSD/huggingface/cyankiwi/Qwen3-Next-80B-A3B-Instruct-AWQ-4bit 8080 $G 0.75 qnext80_x) || exit 1
export POC_BASE_URL=http://127.0.0.1:8080/v1; m=qnext80; X="--stdlib --n_inst 30 --max_tokens 4096"
$P poc/run_geo_cross.py --model_tag X_geox${m}_base $X > results/run_X_geox${m}_base.log 2>&1
$P poc/run_geo_cross.py --model_tag X_geox${m}_pt $X --primitives --prims_task > results/run_X_geox${m}_pt.log 2>&1
for sd in 1 2 3; do $P poc/run_geo_cross.py --model_tag X_geox${m}_base_t07s$sd $X --temperature 0.7 --seed $sd > results/run_X_geox${m}_base_t07s$sd.log 2>&1; done
$P poc/run_geo_cross.py --model_tag X_geox${m}_dis0_t07s1 $X --distract 0 --temperature 0.7 --seed 1 > results/run_X_geox${m}_dis0_t07s1.log 2>&1
$P poc/run_geo_cross.py --model_tag X_geox${m}_dis8_t07s1 $X --distract 8 --temperature 0.7 --seed 1 > results/run_X_geox${m}_dis8_t07s1.log 2>&1
for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do n=${v%%:*}; x=${v#*:}
  $P poc/run_co.py --model_tag X_co${m}_${n} --arms solver $x --repair 2 --temperature 0.7 --seed 1 > results/run_X_co${m}_${n}.log 2>&1; done
kill $S
echo QNEXT_DONE >> results/queue_log.txt
