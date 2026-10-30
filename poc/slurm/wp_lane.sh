#!/bin/bash
# poc/slurm/wp_lane.sh <out dir> <tag> [wp_train.py options]: WP-RL (docs/prereg/PREREG_WPRL.md) — plain RL on Qwen3-8B's non-thinking
# programs for optimization word problems (vLLM with LoRA slots on GPUs 0-1, tensor-parallel, for the rollouts — one 24 GB GPU holds
# KV for only ~15 programs at a time, so sampling took 7 of a round's 12.5 minutes in the smoke — poc/wp_train.py on GPU 2, programs run in the
# sandbox python $P), then the held-out cheap arm formx with the final adapter (a server serving the base as "base" and the adapter as
# "local"; run_form.py <tag> formx, seeds 1-3, on OptiBench's third (FORM_SUBSET=0/3, as HO-PA's think arms), BWOR, LogiOR, OptMATH).
#   sbatch -J wprl -x n19,n22 --gres=gpu:3 --cpus-per-task=12 poc/slurm/job.sh poc/slurm/wp_lane.sh /NAS/SJ/POSTECH/nlp_data/cv/wp1 q8bwp1
# WP_SKIP_TRAIN=1: the evaluation only; WP_NO_EVAL=1: the training only (the smoke); WP_NAME: the log names (default wprl).
out=$1 tag=$2; shift 2
base=/SSD/huggingface/Qwen/Qwen3-8B name=${WP_NAME:-wprl}
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
mkdir -p $out
if [ -z "$WP_SKIP_TRAIN" ]; then
  S=$(bash poc/start_server.sh $base $PORT 0,1 0.90 ${name}_${SLURM_JOB_ID} --max-model-len 8192 --tensor-parallel-size 2 --enable-lora \
    --max-lora-rank 16 --max-loras 2 --max-num-seqs 256) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  POC_PYTHON=$P CUDA_VISIBLE_DEVICES=2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /opt/conda/bin/python poc/wp_train.py $out "$@" >> results/x3/run_${name}_train.log 2>&1
  kill $S; sleep 15
fi
[ -n "$WP_NO_EVAL" ] && { chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $out; exit 0; }
[ -d $out/adapter_final ] || { echo "no adapter_final in $out" >> results/x3/run_${name}_train.log; exit 1; }
S=$(bash poc/start_server.sh $base $PORT 0,1 0.90 ${name}_eval_${SLURM_JOB_ID} --max-model-len 20480 \
  --tensor-parallel-size 2 --served-model-name base --enable-lora --max-lora-rank 16 --max-loras 1 --lora-modules local=$out/adapter_final) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in 1 2 3; do
  NLOPT_SET=optibench FORM_SUBSET=0/3 $P poc/run_form.py $tag formx $s >> results/x3/run_${name}_eval.log 2>&1 &
  for b in bwor logior optmath; do NLOPT_SET=$b $P poc/run_form.py $tag formx $s >> results/x3/run_${name}_eval.log 2>&1 & done
  wait
done
kill $S; sleep 10
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $out
