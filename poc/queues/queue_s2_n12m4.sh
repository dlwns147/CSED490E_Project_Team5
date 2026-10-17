#!/bin/bash
# N12-M4 (PREREG_N.md): Qwen3-8B geometry suite: K8, no helpers, thinking; one seed per GPU (0-2). Tags S2_N10q8_geo_<arm>_s<seed>.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter"
lane() { port=$1 gpu=$2 sd=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $port $gpu 0.88 n12m4_s$sd) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  g() { tag=S2_N10q8_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $tag $GX "$@" > results/run_$tag.log 2>&1; }
  g k8_s$sd --seed $sd --distract 8 --max_tokens 4096 & g none_s$sd --seed $sd --max_tokens 4096 & g think_s$sd --seed $sd --distract 8 --think --max_tokens 16000 & wait
  kill $S; }
lane 8043 0 1 & lane 8044 1 2 & lane 8045 2 3 & wait
echo "S2_N12M4 runs done $(date)" >> results/queue_log.txt
