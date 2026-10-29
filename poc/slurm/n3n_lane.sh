#!/bin/bash
# Nemotron-3-Nano-30B-A3B (HO-N4's settings: 4 x RTX 3090, TP 4) behind poc/slurm/lane.sh: the shared copy lacks the config class its
# config.json names, so a derived dir of links + that file is made first (as poc/slurm/hon_lane.sh --model n3n).
#   sbatch --gres=gpu:4 --cpus-per-task=16 poc/slurm/job.sh poc/slurm/n3n_lane.sh <tag> '<command>' ...
D=/SSD/huggingface/derived/Nemotron-3-Nano-30B-A3B
[ -f $D/configuration_nemotron_h.py ] || { mkdir -p $D && ln -sf /SSD/huggingface/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/* $D/ \
  && cp $POC_DATA/stage/n3n_code/configuration_nemotron_h.py $D/; }
tag=$1; shift
exec bash poc/slurm/lane.sh --gpus 0,1,2,3 --vllm '--max-model-len 24576 --tensor-parallel-size 4 --trust-remote-code --mamba-ssm-cache-dtype float32 --max-num-seqs 128' derived/Nemotron-3-Nano-30B-A3B $tag "$@"
