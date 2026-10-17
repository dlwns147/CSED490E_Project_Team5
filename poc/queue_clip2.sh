#!/bin/bash
# clip follow-up: combine fixes on the hardest task. gpt-oss-20b (GPU 1): low hint s2-3 (hint+MR-select), medium base s1-3 + hint s1-3;
# gpt-oss-120b (GPU 0): low and medium, base s1-3 + hint s1-3. n=60 programs per arm, T=0.7.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--tasks clip --stdlib --n_inst 30 --max_tokens 16000 --temperature 0.7"
l20() { S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8071 1 0.45 oss20_clip2) || { echo "oss20_clip2 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:8071/v1
  for sd in 2 3; do POC_REASONING_EFFORT=low $P poc/run_geo_cross.py --model_tag C2_geoxoss20low_hint_t07s$sd $X --seed $sd --algo_hint > results/run_C2_oss20low_hint_s$sd.log 2>&1; done
  for sd in 1 2 3; do
    POC_REASONING_EFFORT=medium $P poc/run_geo_cross.py --model_tag C2_geoxoss20med_base_t07s$sd $X --seed $sd > results/run_C2_oss20med_base_s$sd.log 2>&1
    POC_REASONING_EFFORT=medium $P poc/run_geo_cross.py --model_tag C2_geoxoss20med_hint_t07s$sd $X --seed $sd --algo_hint > results/run_C2_oss20med_hint_s$sd.log 2>&1
  done; kill $S; }
l120() { S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8072 0 0.88 oss120_clip) || { echo "oss120_clip failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:8072/v1
  for eff in low medium; do t=oss120${eff:0:3}
    for sd in 1 2 3; do
      POC_REASONING_EFFORT=$eff $P poc/run_geo_cross.py --model_tag C2_geox${t}_base_t07s$sd $X --seed $sd > results/run_C2_${t}_base_s$sd.log 2>&1
      POC_REASONING_EFFORT=$eff $P poc/run_geo_cross.py --model_tag C2_geox${t}_hint_t07s$sd $X --seed $sd --algo_hint > results/run_C2_${t}_hint_s$sd.log 2>&1
    done; done; kill $S; }
l20 & A=$!
l120 & B=$!
wait $A $B
echo CLIP2_DONE >> results/queue_log.txt
