#!/bin/bash
# poc/slurm/ifrl_lane.sh <out dir> <bench> <fold 0|1> <server GPU> <trainer GPU> <reward gold|check>: IFRL (docs/prereg/PREREG_IFRL.md) — GRL's loop
# on instruction following (poc/if_train.py) for one fold, then one non-thinking response per held-out prompt with the final adapter
# (served as "local"), seeds 4-6 (IFRL_SEEDS), tag q8bif<r><f> (r = g / c). IFRL_UTIL: vLLM's memory share (0.85; lower when the
# trainer shares the server's GPU). IFRL_BASE_ONLY=1: base rows only (tag q8bif, all prompts, no training; then fold/reward unused).
# Needs PORT, P, POC_DATA, HF_HOME, VLLM_CACHE_ROOT as the other lanes set them; IF_PKGS for the gold grader.
out=$1 B=$2 F=$3 GS=$4 GT=$5 RW=$6
base=/SSD/huggingface/Qwen/Qwen3-8B name=if${B}${RW:0:1}$F tag=q8bif${RW:0:1}$F U=${IFRL_UTIL:-0.85}
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
if [ -n "$IFRL_BASE_ONLY" ]; then
  S=$(bash poc/start_server.sh $base $PORT $GS $U ifbase_$B --max-model-len 8192 --served-model-name local) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  for s in ${IFRL_SEEDS:-4 5 6}; do $P poc/if_train.py --eval $B q8bif $s >> results/run_ifbase_$B.log 2>&1 & done; wait
  kill $S; sleep 10; echo "IFRL base $B done $(date -u)" >> results/run_ifbase_$B.log; exit 0
fi
mkdir -p $out
if [ -z "$IFRL_SKIP_TRAIN" ]; then
  S=$(bash poc/start_server.sh $base $PORT $GS $U ${name}_train --max-model-len 8192 --enable-lora --max-lora-rank 16 --max-loras 2 \
    --max-num-seqs 256) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  POC_PYTHON=$P CUDA_VISIBLE_DEVICES=$GT PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /opt/conda/bin/python poc/if_train.py $out $B $F --reward $RW >> results/run_${name}_train.log 2>&1
  kill $S; sleep 15
fi
[ -d $out/adapter_final ] || { echo "no adapter_final in $out" >> results/run_${name}_train.log; exit 1; }
S=$(bash poc/start_server.sh $base $PORT $GS $U ${name}_eval --max-model-len 8192 --served-model-name base --enable-lora \
  --max-lora-rank 16 --max-loras 1 --lora-modules local=$out/adapter_final) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in ${IFRL_SEEDS:-4 5 6}; do $P poc/if_train.py --eval $B $tag $s --ids $POC_DATA/if_rl/${B}_fold${F}_ids.txt >> results/run_${name}_eval.log 2>&1 & done
wait
kill $S; sleep 10
echo "IFRL $name done $(date -u)" >> results/run_${name}_eval.log
