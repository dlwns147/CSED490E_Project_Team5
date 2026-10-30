#!/bin/bash
# poc/slurm/cv_eval_lane.sh <arm> <tag> <adapter dir> <seed> ...: CV-1's dev evaluation alone (cv_lane.sh's CV_EVAL step, same server)
# for an adapter already trained.
#   sbatch -J cv_eval_c1 -x n19,n22 poc/slurm/job.sh poc/slurm/cv_eval_lane.sh c1 q8bcvc1 /NAS/SJ/POSTECH/nlp_data/cv/c1/adapter_final 2 3
arm=$1 tag=$2 adapter=$3; shift 3
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
S=$(bash poc/start_server.sh ${CV_BASE:-/SSD/huggingface/Qwen/Qwen3-8B} $PORT 0 0.90 cv_eval_${arm}_${SLURM_JOB_ID} --max-model-len 8192 --enable-lora \
  --max-lora-rank 16 --max-loras 2 --max-num-seqs 128) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in "$@"; do /opt/conda/bin/python poc/cv_eval.py $arm $tag $adapter $s >> results/sql/run_cv_eval_${arm}.log 2>&1; done
kill $S; sleep 10
