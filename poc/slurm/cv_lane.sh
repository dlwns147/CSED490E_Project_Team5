#!/bin/bash
# poc/slurm/cv_lane.sh <arm> <out dir> [cv_train.py options]: one CV-1 training (docs/prereg/PREREG_CV.md) — vLLM serving Qwen3-8B with
# LoRA slots on GPU 0 for the rollouts, the trainer (poc/cv_train.py) on GPU 1. Optional after the training: CV_EVAL='<arm> <tag> <adapter dir>' runs
# poc/cv_eval.py on BIRD dev for seeds 1-3 (CV_SEEDS to change them).
#   sbatch -J cv_cv -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/cv_lane.sh cv /NAS/SJ/POSTECH/nlp_data/cv/cv
# CV_BASE: the base model (default Qwen3-8B; also pass --base to cv_train.py); CV_NAME: the log name (default <arm>).
arm=$1 out=$2; shift 2
name=${CV_NAME:-$arm}
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
S=$(bash poc/start_server.sh ${CV_BASE:-/SSD/huggingface/Qwen/Qwen3-8B} $PORT 0 0.90 cv_${arm}_${SLURM_JOB_ID} --max-model-len 8192 --enable-lora \
  --max-lora-rank 16 --max-loras 2 --max-num-seqs 128) || exit 1
mkdir -p $out
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
CUDA_VISIBLE_DEVICES=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CV_WORKERS=6 \
  /opt/conda/bin/python poc/cv_train.py $arm $out "$@" >> results/sql/run_cv_train_${name}.log 2>&1
[ -n "$CV_EVAL" ] && for s in ${CV_SEEDS:-1 2 3}; do /opt/conda/bin/python poc/cv_eval.py $CV_EVAL $s >> results/sql/run_cv_eval_${name}.log 2>&1; done
kill $S; sleep 10
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $out
