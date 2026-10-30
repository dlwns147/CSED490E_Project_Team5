#!/bin/bash
# poc/slurm/tc_lane.sh <out dir> <tag> [tc_train.py options]: TC-RL (docs/prereg/PREREG_TCRL.md) — plain RL on Qwen3-8B's non-thinking
# tool calls (vLLM with LoRA slots on GPU 0 for the rollouts, poc/tc_train.py on GPU 1), then BFCL's quick calls with the final adapter
# (a server serving the base as "base" and the adapter as "local", run_tc.py TC_ARMS=quick, seeds 1-3, tag <tag>).
#   sbatch -J tcrl -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/tc_lane.sh /NAS/SJ/POSTECH/nlp_data/cv/tc1 q8btcc1
# TC_SKIP_TRAIN=1: the evaluation only (the adapter exists); TC_NO_EVAL=1: the training only (the smoke).
out=$1 tag=$2; shift 2
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
mkdir -p $out
if [ -z "$TC_SKIP_TRAIN" ]; then
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0 0.90 tcrl_${SLURM_JOB_ID} --max-model-len 8192 --enable-lora \
    --max-lora-rank 16 --max-loras 2 --max-num-seqs 128) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  CUDA_VISIBLE_DEVICES=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /opt/conda/bin/python poc/tc_train.py $out "$@" >> results/tc/run_tcrl_train.log 2>&1
  kill $S; sleep 15
fi
[ -n "$TC_NO_EVAL" ] && { chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $out; exit 0; }
[ -d $out/adapter_final ] || { echo "no adapter_final in $out" >> results/tc/run_tcrl_train.log; exit 1; }
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0,1 0.90 tcrl_eval_${SLURM_JOB_ID} --max-model-len 20480 \
  --tensor-parallel-size 2 --served-model-name base --enable-lora --max-lora-rank 16 --max-loras 1 --lora-modules local=$out/adapter_final) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in 1 2 3; do TC_ARMS=quick $P poc/run_tc.py $tag $s >> results/tc/run_tcrl_eval.log 2>&1; done
kill $S; sleep 10
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $out
