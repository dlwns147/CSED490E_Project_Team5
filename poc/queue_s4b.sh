#!/bin/bash
# S4b/S4c: why do primitives HURT 32B on hull/close? ablate task-matched predicates vs format reminder; + 32B S2b
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8023 q32b_s4b)
export POC_BASE_URL=http://127.0.0.1:8023/v1
$P poc/run_geo_cross.py --model_tag geox32b_prims_fmt --primitives --fmt_after --max_tokens 4096 > results/run_geox32b_prims_fmt.log 2>&1
$P poc/run_geo_cross.py --model_tag geox32b_prims_task --primitives --prims_task --max_tokens 4096 > results/run_geox32b_prims_task.log 2>&1
$P poc/run_geo_cross.py --model_tag geox32b_prims_task_fmt --primitives --prims_task --fmt_after --max_tokens 4096 > results/run_geox32b_prims_task_fmt.log 2>&1
kill $S
echo S4B_DONE >> results/queue_s4b.log
