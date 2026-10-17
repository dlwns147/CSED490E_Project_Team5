#!/bin/bash
# E5 step 1 (data): self-distillation data for "can robustness to irrelevant helpers be learned?" Teacher = Qwen3-8B WITH thinking
# (robust: -1.5 points under K8) on TRAINING instances disjoint from every eval instance (--inst_prefix train-), 5 core geometry tasks,
# n_inst 60 (600 prompts per K), toolbox K = 0 / 4 / 8 ("should" header), prompts saved; programs are later filtered by the oracle.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $1 $2 0.45 q8b_e5gen_k$3) || { echo "e5gen k$3 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$1/v1
  $P poc/run_geo_cross.py --model_tag T_geox8b_train_k$3_think --inst_prefix train- --save_prompt --stdlib --n_inst 60 --distract $3 \
     --think --max_tokens 16000 --temperature 0.7 --seed 1 > results/run_T_geox8b_train_k$3.log 2>&1
  kill $S; }
lane 8040 0 0 & L1=$!
sleep 30
lane 8041 1 8 & L2=$!
sleep 30
lane 8042 3 4 & L3=$!
wait $L1 $L2 $L3
echo E5GEN_DONE >> results/queue_log.txt
