#!/bin/bash
# F3x (pre-registered in FINDINGS 2026-10-13 12:40): Qwen3-32B-AWQ diameter K0 / LOW with the literal stdin shown. Port 8042 (GPU 2).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_BASE_URL=http://127.0.0.1:8042/v1
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --tasks diameter --show_stdin"
for sd in 1 2; do
  $P poc/run_geo_cross.py --model_tag S2_F3x_geox32b_diam_k0_ex_t07s$sd $X --seed $sd > results/run_S2_F3x_k0_s$sd.log 2>&1 &
  $P poc/run_geo_cross.py --model_tag S2_F3x_geox32b_diam_low_ex_t07s$sd $X --seed $sd --distract 0 \
     --distract_set '{"diameter": ["point_in_polygon", "segments_intersect"]}' > results/run_S2_F3x_low_s$sd.log 2>&1 &
done
wait
echo "S2_F3x done $(date)" >> results/queue_log.txt
