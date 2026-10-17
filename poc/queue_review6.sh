#!/bin/bash
# Review item 6: prompt sensitivity. Two paraphrased instruction templates (variants 1, 2; variant 0 = the original) x neutral toolbox K=0 / K=8, n=300, --stdlib, T=0.7 s1.
# + X1 on CLEAN prompts (8B, no helpers): samples s4-s6 vs thinking budgets 256/1024 vs full thinking, token-accounted, n=100.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start /SSD/huggingface/Qwen/$1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for pv in 1 2; do for k in 0 8; do $P poc/run_geo_cross.py --model_tag F_geox${m}_dis${k}neu_pv${pv}_t07s1 --stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1 --distract $k --tb_head neutral --prompt_variant $pv > results/run_F_geox${m}_dis${k}neu_pv$pv.log 2>&1; done; done
  if [ "$m" = "8b" ]; then X="--stdlib --temperature 0.7 --max_tokens 4096"
    for sd in 4 5 6; do $P poc/run_geo_cross.py --model_tag C_geox8b_base_t07s$sd $X --seed $sd > results/run_C_geox8b_base_s$sd.log 2>&1; done
    for B in 256 1024; do $P poc/run_geo_cross.py --model_tag C_geox8b_base_b$B $X --seed 4 --think_budget $B > results/run_C_geox8b_base_b$B.log 2>&1; done
    $P poc/run_geo_cross.py --model_tag C_geox8b_base_think --stdlib --temperature 0.7 --seed 4 --think --max_tokens 20000 > results/run_C_geox8b_base_think.log 2>&1
  fi
  kill $S; }
lane Qwen3-8B 8072 q8b_rv6 8b & L1=$!
sleep 30
lane Qwen3-14B 8073 q14b_rv6 14b & L2=$!
sleep 30
lane Qwen3-32B-AWQ 8074 q32b_rv6 32b & L3=$!
wait $L1 $L2 $L3
echo REVIEW6_DONE >> results/queue_log.txt
