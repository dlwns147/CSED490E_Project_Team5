#!/bin/bash
# B2 (results/PREREG_B2.md): evaluate one model dir. usage: bash poc/queue_s2_b2eval.sh <name> <model_dir> <port> <gpu> [frac]
# Same evaluation as E4 (queue_s2_e4eval.sh): hull K0/K8 s1-2, 4 trained tasks K8 s1, diameter s1, delaunay-fixed s1. Tags S2_B2_<name>_*.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
name=$1 dir=$2 port=$3 gpu=$4
S=$(bash poc/start_server.sh $dir $port $gpu ${5:-0.45} b2_$name) || { echo "b2 eval $name: server failed $(date)" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:$port/v1
X="--stdlib --n_inst 30 --max_tokens 4096 --temperature 0.7"
r() { tag=S2_B2_${name}_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $X "$@" > results/run_$tag.log 2>&1; }
for k in 0 8; do for sd in 1 2; do r hull_k${k}_s$sd --tasks hull --seed $sd --distract $k & done; done
r trained_k8_s1 --tasks area2,pip,segs,close --seed 1 --distract 8 &
r diam_s1 --tasks diameter --seed 1 &
r delfixed_s1 --tasks delaunay --seed 1 --distract 0 --incircle fixed &
wait
kill $S
echo "S2_B2 eval $name done $(date)" >> results/queue_log.txt
