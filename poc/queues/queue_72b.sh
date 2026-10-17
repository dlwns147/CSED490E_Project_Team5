#!/bin/bash
# Fifth scale point: Qwen2.5-72B-Instruct (no thinking mode), tensor-parallel over 4 GPUs at 0.6 each (~32 GB headroom per GPU
# for other users). No-think arms of every headline fix.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for g in 0 1 2 3; do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $g); [ "$u" -lt 20000 ] || { echo "GPU $g busy ($u MiB), abort"; exit 1; }; done
poc/serve_gpu.sh /SSD/huggingface/Qwen/Qwen2.5-72B-Instruct 8057 0,1,2,3 0.6 --tensor-parallel-size 4 > results/server_vllm_q72b.log 2>&1 9>&- &
S=$!; echo "q72b: GPUs 0-3 frac 0.6 TP4 port 8057 ($(date))" >> results/gpu_choice.log
until curl -sf localhost:8057/health >/dev/null; do kill -0 $S 2>/dev/null || { echo "q72b failed" >> results/gpu_choice.log; exit 1; }; sleep 10; done
export POC_BASE_URL=http://127.0.0.1:8057/v1; m=72b
$P poc/run_geo_cross.py --model_tag geox${m} --max_tokens 2048 > results/run_geox${m}.log 2>&1
$P poc/run_geo_cross.py --model_tag geox${m}_prims --primitives --max_tokens 2048 > results/run_geox${m}_prims.log 2>&1
$P poc/run_geo_cross.py --model_tag geox${m}_prims_task --primitives --prims_task --max_tokens 2048 > results/run_geox${m}_prims_task.log 2>&1
$P poc/run_co.py --model_tag co${m}_nodoc_r2_v2 --arms solver --repair 2 > results/run_co${m}_nodoc_v2.log 2>&1
$P poc/run_co.py --model_tag co${m}_doc_r2_v2 --arms solver --api_doc --repair 2 > results/run_co${m}_doc_v2.log 2>&1
$P poc/run_co.py --model_tag co${m}_doctask_r2_v2 --arms solver --api_doc_task --repair 2 > results/run_co${m}_doctask_v2.log 2>&1
$P poc/run_zebra.py --model_tag z${m}_nothink --max_tokens 4096 > results/run_zebra_z${m}_nothink.log 2>&1
$P poc/run_zebra.py --model_tag z${m}_nothink_docst --arms code --api_doc --doc_status --max_tokens 4096 > results/run_zebra_z${m}_nothink_docst.log 2>&1
$P poc/run_games.py --model_tag mm${m}_code_rep2 --games mastermind --code --code_repair 2 --max_tokens 4096 > results/run_games_mm${m}_code_rep2.log 2>&1
kill $S
echo Q72B_DONE >> results/queue_72b.log
