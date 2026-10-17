#!/bin/bash
# Does thinking help LLM-written CG/CO code once the facts are stated? geometry (stdlib) base / task-matched with --think (n=100, T=0.7 s1);
# CO scoped snippet + repair with --think (84 instances, s1). Compare with the no-think arms at the same settings.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; G="--stdlib --temperature 0.7 --seed 1 --max_tokens 20000 --think"
  $P poc/run_geo_cross.py --model_tag T_geox${m}_base $G > results/run_T_geox${m}_base.log 2>&1
  $P poc/run_geo_cross.py --model_tag T_geox${m}_pt $G --primitives --prims_task > results/run_T_geox${m}_pt.log 2>&1
  $P poc/run_co.py --model_tag T_co${m}_doctask --arms solver --api_doc_task --repair 2 --temperature 0.7 --seed 1 --think --max_tokens 20000 > results/run_T_co${m}_doctask.log 2>&1
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8068 q8b_think 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8069 q14b_think 14b & L2=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8070 q32b_think 32b & L3=$!
wait $L1 $L2 $L3
echo THINK_DONE >> results/queue_distract.log
