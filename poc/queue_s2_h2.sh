#!/bin/bash
# H2 (results/PREREG_H2.md): contest geometry. Servers: 8040 Qwen3-8B, 8041 Qwen3-32B-AWQ, 8042 gpt-oss-20b, 8043 gpt-oss-120b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
r() { port=$1 eff=$2 tag=$3 sd=$4; shift 4; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
      $P poc/run_cc.py run $tag $sd "$@" > results/h2/run_${tag}_s$sd.log 2>&1 ); }
for sd in 1 2 3; do
  for mp in "8b 8040" "32b 8041"; do set -- $mp
    r $2 "" q$1_plain $sd & r $2 "" q$1_k8 $sd --k8 & r $2 "" q$1_think1024 $sd --think_budget 1024 & r $2 "" q$1_think $sd --think &
  done
  for mp in "oss20 8042" "oss120 8043"; do set -- $mp
    r $2 low $1_low $sd --max_tokens 16000 & r $2 medium $1_medium $sd --max_tokens 16000 &
  done
  wait
done
echo "S2_H2 runs done $(date)" >> results/queue_log.txt
