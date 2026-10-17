#!/bin/bash
# H1 (results/PREREG_H1.md): large-input tasks. 8040 Qwen3-8B, 8041 Qwen3-32B-AWQ, 8042 gpt-oss-20b (low), 8043 gpt-oss-120b (low).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
X="--stdlib --n_inst 20 --max_tokens 4096 --temperature 0.7 --tasks hullL,closeL,diamL --fast_fail"
r() { port=$1 eff=$2 tag=$3; shift 3; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
      $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1 ); }
for sd in 1 2; do
  for mp in "8b 8040" "32b 8041"; do set -- $mp
    r $2 "" S2_H1_geox$1_bare_t07s$sd --seed $sd &
    r $2 "" S2_H1_geox$1_k8_t07s$sd --seed $sd --distract 8 &
    r $2 "" S2_H1_geox$1_think1024_t07s$sd --seed $sd --distract 8 --think_budget 1024 &
    r $2 "" S2_H1_geox$1_m4_t07s$sd --seed $sd --distract 8 --algo_first &
  done
  for mp in "oss20low 8042" "oss120low 8043"; do set -- $mp
    r $2 low S2_H1_geox$1_bare_t07s$sd --seed $sd --max_tokens 16000 &
    r $2 low S2_H1_geox$1_k8_t07s$sd --seed $sd --distract 8 --max_tokens 16000 &
  done
  wait
done
echo "S2_H1 runs done $(date)" >> results/queue_log.txt
