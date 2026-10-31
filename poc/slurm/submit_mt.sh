#!/bin/bash
# MT (docs/prereg/PREREG_MT.md): one job per model and seed; the four arms run as four clients against one server
# (rows results/tc/mt_<tag>_<arm>_s<seed>.jsonl, logs results/run_mt_<tag>_s<seed>.log). Qwen3-8B on two 3090s (TP 2), as LC-1;
# from 2026-10-31 15:1x UTC Qwen3-14B-AWQ and Qwen3.5-9B too (on one 3090 their KV caches were full, prefix hits 12-41%, ~30-110 tokens/s).
#   [MT_MODELS="q14a q35"] [MT_X=n19,n22,...] bash poc/slurm/submit_mt.sh [seeds ...]   (rows resume; MT_X: nodes to exclude)
cd /home1/leesangjun/SJ/POSTECH/nlp
arms() { for a in N E F T; do printf '%s\0' "MT_WORKERS=6 \$P poc/run_mt.py $1 $a $2"; done; }
TP2="-x ${MT_X:-n19,n22} --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --gpus 0,1"
for s in ${@:-1 2 3}; do
  for m in ${MT_MODELS:-q14a q35 q8b}; do
    mapfile -d '' C < <(arms $m $s)
    case $m in
      q14a) sbatch -J mt_q14a_s$s $TP2 --vllm '--max-model-len 32768 --tensor-parallel-size 2' Qwen/Qwen3-14B-AWQ mt_q14a_s$s "${C[@]}" ;;
      q35) sbatch -J mt_q35_s$s $TP2 --vllm '--max-model-len 32768 --language-model-only --max-num-seqs 32 --tensor-parallel-size 2' \
             Qwen/Qwen3.5-9B mt_q35_s$s "${C[@]}" ;;
      q8b) sbatch -J mt_q8b_s$s $TP2 --vllm '--max-model-len 32768 --tensor-parallel-size 2' Qwen/Qwen3-8B mt_q8b_s$s "${C[@]}" ;;
    esac
  done
done
