#!/bin/bash
# Firm up Llama-3.3-70B's weak distractor effect (−4.0, CI [−9.3,+1.0] on seed 1): seeds 2-3 of K=0 / K=8 (n=300, --stdlib, T=0.7) + K=8 prelude (s1).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
while true; do G=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 5000 {print $1; exit}'); [ -n "$G" ] && break; sleep 120; done
S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/Llama-3.3-70B-Instruct-quantized.w4a16 8076 $G 0.7 llama70_dis) || exit 1
export POC_BASE_URL=http://127.0.0.1:8076/v1; m=llama70; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
for sd in 2 3; do for k in 0 8; do $P poc/run_geo_cross.py --model_tag X_geox${m}_dis${k}_t07s$sd $X --seed $sd --distract $k > results/run_X_geox${m}_dis${k}_s$sd.log 2>&1; done; done
$P poc/run_geo_cross.py --model_tag X_geox${m}_dis8pre_t07s1 $X --seed 1 --distract 8 --tb_head prelude > results/run_X_geox${m}_dis8pre.log 2>&1
$P poc/run_geo_cross.py --model_tag X_geox${m}_dis0pre_t07s1 $X --seed 1 --distract 0 --tb_head prelude > results/run_X_geox${m}_dis0pre.log 2>&1
kill $S
echo L70DIS_DONE >> results/queue_log.txt
