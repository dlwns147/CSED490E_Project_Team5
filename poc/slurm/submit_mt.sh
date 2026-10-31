#!/bin/bash
# MT (docs/prereg/PREREG_MT.md): one job per model and seed; the four arms run as four clients against one server
# (rows results/tc/mt_<tag>_<arm>_s<seed>.jsonl, logs results/run_mt_<tag>_s<seed>.log). Qwen3-8B on two 3090s (TP 2), as LC-1.
#   bash poc/slurm/submit_mt.sh [seeds ...]
cd /home1/leesangjun/SJ/POSTECH/nlp
arms() { for a in N E F T; do printf '%s\0' "MT_WORKERS=6 \$P poc/run_mt.py $1 $a $2"; done; }
for s in ${@:-1 2 3}; do
  mapfile -d '' C < <(arms q14a $s)
  sbatch -J mt_q14a_s$s -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 32768' Qwen/Qwen3-14B-AWQ mt_q14a_s$s "${C[@]}"
  mapfile -d '' C < <(arms q35 $s)
  sbatch -J mt_q35_s$s -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 32768 --language-model-only --max-num-seqs 32' \
    Qwen/Qwen3.5-9B mt_q35_s$s "${C[@]}"
  mapfile -d '' C < <(arms q8b $s)
  sbatch -J mt_q8b_s$s -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --gpus 0,1 \
    --vllm '--max-model-len 32768 --tensor-parallel-size 2' Qwen/Qwen3-8B mt_q8b_s$s "${C[@]}"
done
