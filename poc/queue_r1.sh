#!/bin/bash
# E1 (reasoning-model family): DeepSeek-R1-Distill-Llama-70B (w4a16, one GPU at 0.7). Geometry --stdlib n=100: no helpers / task-matched / K=0 vs K=8
# toolbox (T=0.6, R1's recommended temperature) + CO 84 inst: no doc / full / scoped. Long reasoning: max_tokens 16000. Runs from the POSTECH base folder.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
while true; do G=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 5000 {print $1; exit}'); [ -n "$G" ] && break; sleep 120; done
S=$(poc/start_server.sh /SSD/huggingface/RedHatAI/DeepSeek-R1-Distill-Llama-70B-quantized.w4a16 8075 $G 0.7 r1llama70_x) || exit 1
export POC_BASE_URL=http://127.0.0.1:8075/v1; m=r1l70; X="--stdlib --max_tokens 16000 --temperature 0.6 --seed 1"
$P poc/run_geo_cross.py --model_tag X_geox${m}_base_t06s1 $X > results/run_X_geox${m}_base.log 2>&1
$P poc/run_geo_cross.py --model_tag X_geox${m}_pt_t06s1 $X --primitives --prims_task > results/run_X_geox${m}_pt.log 2>&1
$P poc/run_geo_cross.py --model_tag X_geox${m}_dis0_t06s1 $X --distract 0 > results/run_X_geox${m}_dis0.log 2>&1
$P poc/run_geo_cross.py --model_tag X_geox${m}_dis8_t06s1 $X --distract 8 > results/run_X_geox${m}_dis8.log 2>&1
for v in "nodoc:" "doc:--api_doc" "doctask:--api_doc_task"; do n=${v%%:*}; x=${v#*:}
  $P poc/run_co.py --model_tag X_co${m}_${n} --arms solver $x --repair 2 --temperature 0.6 --seed 1 --max_tokens 16000 > results/run_X_co${m}_${n}.log 2>&1; done
kill $S
echo R1_DONE >> results/queue_log.txt
