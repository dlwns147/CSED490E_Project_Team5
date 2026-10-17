#!/bin/bash
# Chained after queue_e5c.sh. E5d: is the learned robustness tied to the training prompt format? Eval the E5 mixed LoRA (trained on
# "should use" header, K 0/4/8) and the base model on the main 5 tasks with: neutral header K8, K10 (more helpers than seen),
# 6 UNRELATED helpers, prelude header K8 (helpers pre-defined). T=0.7 s1, no thinking. GPU 0 (mixed) / GPU 1 (base).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
while kill -0 796474 2>/dev/null; do sleep 60; done
ev() { S=$(poc/start_server.sh $1 $2 $3 0.45 e5d_$4) || { echo "e5d $4 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7 --seed 1"
  $P poc/run_geo_cross.py --model_tag E5D_geox${m}_k8neu $X --distract 8 --tb_head neutral > results/run_E5D_${m}_k8neu.log 2>&1
  $P poc/run_geo_cross.py --model_tag E5D_geox${m}_k10 $X --distract 10 > results/run_E5D_${m}_k10.log 2>&1
  $P poc/run_geo_cross.py --model_tag E5D_geox${m}_unrel6 $X --distract 6 --distract_kind unrelated > results/run_E5D_${m}_unrel6.log 2>&1
  $P poc/run_geo_cross.py --model_tag E5D_geox${m}_k8pre $X --distract 8 --tb_head prelude > results/run_E5D_${m}_k8pre.log 2>&1
  kill $S; }
ev /dev/shm/e5_mixed 8056 0 mixed & A=$!
ev /SSD/huggingface/Qwen/Qwen3-8B 8057 1 base & B=$!
wait $A $B
echo E5D_DONE >> results/queue_log.txt
