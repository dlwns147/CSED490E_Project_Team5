#!/bin/bash
# E4 (docs/prereg/PREREG_E4_REPLAY.md): evaluate one merged LoRA model. usage: bash poc/queues/queue_s2_e4eval.sh <arm> <port> <gpu> [frac]
# Serves /dev/shm/e4_<arm>, runs: hull K0/K8 seeds 1-2 (unseen task); the 4 trained tasks under K8 seed 1; unseen new tasks diameter (no toolbox)
# and delaunay (fixed in_circle) seed 1. Tags S2_E4_<arm>_*. Shuts the server down afterwards (the merged model stays in /dev/shm).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
arm=$1 port=$2 gpu=$3
S=$(bash poc/start_server.sh /dev/shm/e4_$arm $port $gpu ${4:-0.40} e4_$arm) || { echo "e4 eval $arm: server failed $(date)" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:$port/v1
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
r() { tag=S2_E4_${arm}_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1; }
for k in 0 8; do for sd in 1 2; do r hull_k${k}_s$sd --tasks hull --seed $sd --distract $k & done; done
r trained_k8_s1 --tasks area2,pip,segs,close --seed 1 --distract 8 &
r diam_s1 --tasks diameter --seed 1 &
r delfixed_s1 --tasks delaunay --seed 1 --distract 0 --incircle fixed &
wait
kill $S
echo "S2_E4 eval $arm done $(date)" >> results/queue_log.txt
