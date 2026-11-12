#!/bin/bash
# poc/slurm/gpk_lane.sh <tag> <GPU> [<adapter dir> <ids file>]: GRLK (docs/prereg/PREREG_GRLK.md) — 128 first-round quick grid translations per
# puzzle (poc/gp_passk.py) from Qwen3-8B, or from the GRL adapter (served as "local") on that fold's held-out puzzles.
# Needs PORT, P, POC_DATA, HF_HOME, VLLM_CACHE_ROOT as the other lanes set them.
tag=$1 G=$2 ad=$3 ids=$4
base=/SSD/huggingface/Qwen/Qwen3-8B
if [ -n "$ad" ]; then
  S=$(bash poc/start_server.sh $base $PORT $G 0.85 gpk_$tag --max-model-len 8192 --served-model-name base --enable-lora --max-lora-rank 16 \
    --max-loras 1 --lora-modules local=$ad --max-num-seqs 256) || exit 1
else
  S=$(bash poc/start_server.sh $base $PORT $G 0.85 gpk_$tag --max-model-len 8192 --max-num-seqs 256) || exit 1
fi
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
$P poc/gp_passk.py $tag ${ids:+--ids $ids} >> results/run_gpk_$tag.log 2>&1
kill $S; sleep 10
echo "GPK $tag done $(date -u)" >> results/run_gpk_$tag.log
