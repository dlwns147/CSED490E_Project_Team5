#!/bin/bash
# Model-scale sweep of the headline fixes: Qwen3-1.7B and Qwen3-14B fill in the 8B -> 32B gap.
# Per model: geometry (base / all predicates / task-matched), zebra (direct, code, code+snippet; no-think and think),
# Mastermind (code policy; + think + consistency check), CO solver (no doc / full doc / scoped snippet).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {  # lane <model> <port> <tag> <short>
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  $P poc/run_geo_cross.py --model_tag geox${m} --max_tokens 2048 > results/run_geox${m}.log 2>&1
  $P poc/run_geo_cross.py --model_tag geox${m}_prims --primitives --max_tokens 2048 > results/run_geox${m}_prims.log 2>&1
  $P poc/run_geo_cross.py --model_tag geox${m}_prims_task --primitives --prims_task --max_tokens 2048 > results/run_geox${m}_prims_task.log 2>&1
  $P poc/run_co.py --model_tag co${m}_nodoc_r2_v2 --arms solver --repair 2 > results/run_co${m}_nodoc_v2.log 2>&1
  $P poc/run_co.py --model_tag co${m}_doc_r2_v2 --arms solver --api_doc --repair 2 > results/run_co${m}_doc_v2.log 2>&1
  $P poc/run_co.py --model_tag co${m}_doctask_r2_v2 --arms solver --api_doc_task --repair 2 > results/run_co${m}_doctask_v2.log 2>&1
  $P poc/run_zebra.py --model_tag z${m}_nothink --max_tokens 4096 > results/run_zebra_z${m}_nothink.log 2>&1
  $P poc/run_zebra.py --model_tag z${m}_nothink_doc --arms code --api_doc --max_tokens 4096 > results/run_zebra_z${m}_nothink_doc.log 2>&1
  $P poc/run_games.py --model_tag mm${m}_code_rep2 --games mastermind --code --code_repair 2 --max_tokens 4096 > results/run_games_mm${m}_code_rep2.log 2>&1
  $P poc/run_zebra.py --model_tag z${m}_think --think --max_tokens 20000 > results/run_zebra_z${m}_think.log 2>&1
  $P poc/run_zebra.py --model_tag z${m}_think_doc --arms code --api_doc --think --max_tokens 20000 > results/run_zebra_z${m}_think_doc.log 2>&1
  $P poc/run_games.py --model_tag mm${m}_code_think20k_cons --games mastermind --code --think --code_repair 2 --no_repeat --consistent_check --max_tokens 20000 > results/run_games_mm${m}_code_think20k_cons.log 2>&1
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-14B 8050 q14b_scale 14b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-1.7B 8051 q1_7b_scale 1_7b & L2=$!
wait $L1 $L2
echo SCALE_DONE >> results/queue_scale.log
