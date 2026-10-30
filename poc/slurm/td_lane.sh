#!/bin/bash
# poc/slurm/td_lane.sh <arm td|rft> <data tag> <eval tag>: TD (docs/prereg/PREREG_TD.md) — LoRA SFT of Qwen3-8B on one SFT set
# ($POC_DATA/optmath_train/td/sft_<arm>_<data tag>.jsonl, poc/td_build.py; DT's recipe: poc/sft_lora.py, r 16, 2 epochs, lr 1e-4, on
# GPUs 0-1), merged to /SSD/huggingface/derived/Qwen3-8B-td-<arm>, then the held-out cheap arm formx with it (one server on GPU 0;
# run_form.py <eval tag> formx, seeds 1-3, OptiBench's third / BWOR / LogiOR / OptMATH, as WP-RL's evaluation).
#   sbatch -J td_<arm> -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh "bash poc/slurm/td_lane.sh <arm> <data tag> <eval tag>"
arm=$1 dtag=$2 tag=$3
D=/NAS/SJ/POSTECH/nlp_data/optmath_train/td M=/SSD/huggingface/derived/Qwen3-8B-td-$arm
if [ ! -f $M/config.json ]; then
  CUDA_VISIBLE_DEVICES=0,1 /opt/conda/bin/python poc/sft_lora.py /SSD/huggingface/Qwen/Qwen3-8B $D/sft_${arm}_$dtag.jsonl $D/adapter_$arm $M \
    >> results/x3/run_td_${arm}_train.log 2>&1 || exit 1
fi
S=$(bash poc/start_server.sh $M $PORT 0 0.92 td_${arm}_$SLURM_JOB_ID --max-model-len 20480) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in 1 2 3; do
  NLOPT_SET=optibench FORM_SUBSET=0/3 $P poc/run_form.py $tag formx $s >> results/x3/run_td_${arm}_eval.log 2>&1 &
  for b in bwor logior optmath; do NLOPT_SET=$b $P poc/run_form.py $tag formx $s >> results/x3/run_td_${arm}_eval.log 2>&1 & done
  wait
done
kill $S; sleep 10
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $D
