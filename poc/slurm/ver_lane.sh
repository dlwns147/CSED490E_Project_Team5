#!/bin/bash
# poc/slurm/ver_lane.sh <name>: VER (docs/prereg/PREREG_VER.md) — Qwen3-8B as a verifier of passing word-problem programs. LoRA SFT on
# $POC_DATA/optmath_train/sft_ver_<name>.jsonl (poc/ver_build.py; DT's recipe, 1 epoch, data-parallel over the job's 4 GPUs; if that
# fails, on GPUs 0-1 with the model split as td_lane.sh), merged to /SSD/huggingface/derived/Qwen3-8B-ver-<name>; then the base model
# (tag ver0) and the trained one (tag ver<name>) score the stored programs and the train-dev set (poc/ver_score.py), one server each.
#   sbatch -J ver_<name> -x n19,n22 --gres=gpu:4 --cpus-per-task=16 poc/slurm/job.sh "bash poc/slurm/ver_lane.sh <name>"
name=$1
D=/NAS/SJ/POSTECH/nlp_data/optmath_train M=/SSD/huggingface/derived/Qwen3-8B-ver-$name B=/SSD/huggingface/Qwen/Qwen3-8B
L=results/x3/run_ver_${name}_train.log
if [ ! -f $M/config.json ]; then
  CUDA_VISIBLE_DEVICES=0,1,2,3 /opt/conda/bin/python -m torch.distributed.run --nproc_per_node 4 poc/sft_lora.py $B $D/sft_ver_$name.jsonl \
    $D/td/adapter_ver_$name $M --epochs 1 >> $L 2>&1 \
  || { echo "data-parallel training failed ($(date -u)); model split over GPUs 0-1" >> $L
       CUDA_VISIBLE_DEVICES=0,1 /opt/conda/bin/python poc/sft_lora.py $B $D/sft_ver_$name.jsonl $D/td/adapter_ver_$name $M --epochs 1 >> $L 2>&1 \
       || exit 1; }
fi
S0=$(bash poc/start_server.sh $B $PORT 0 0.92 ver0_$SLURM_JOB_ID --max-model-len 20480) || exit 1
S1=$(bash poc/start_server.sh $M $((PORT + 1)) 1 0.92 ver${name}_$SLURM_JOB_ID --max-model-len 20480) || exit 1
POC_BASE_URL=http://127.0.0.1:$PORT/v1 $P poc/ver_score.py ver0 $name >> results/x3/run_ver_score.log 2>&1 &
POC_BASE_URL=http://127.0.0.1:$((PORT + 1))/v1 $P poc/ver_score.py ver$name $name >> results/x3/run_ver_score.log 2>&1 &
wait
kill $S0 $S1; sleep 10
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $D/td
