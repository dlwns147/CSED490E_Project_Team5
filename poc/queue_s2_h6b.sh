#!/bin/bash
# H6 continued with four Qwen3.8-27B-FP8 servers (8046 GPU0, 8047 GPU3, 8048 GPU1, 8049 GPU2); seeds run in parallel.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
cc() { port=$1 tag=$2 sd=$3; shift 3; POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run $tag $sd "$@" > results/h2/run_full_${tag}_s$sd.log 2>&1; }
so() { port=$1 arm=$2; shift 2; for sd in 1 2; do POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_solomon.py run q38_$arm $sd "$@" > results/h3/run_q38_${arm}_s$sd.log 2>&1; done; }
( while kill -0 3858783 2>/dev/null; do sleep 30; done; cc 8046 q38_plain 2 & cc 8046 q38_plain 3 & wait ) &
( cc 8048 q38_k8 1 --k8 & cc 8048 q38_k8 2 --k8 & cc 8048 q38_k8 3 --k8 & wait ) &
( so 8049 plain & so 8049 docs --snippet & so 8049 parserintrobust --parser_int --snippet_robust & wait ) &
( while kill -0 3858784 2>/dev/null; do sleep 30; done ) &
wait
echo "S2_H6 runs done $(date)" >> results/queue_log.txt
