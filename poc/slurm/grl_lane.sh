#!/bin/bash
# poc/slurm/grl_lane.sh <out dir> <fold 0|1> <server GPU> <trainer GPU> [gp_train.py options]: GRL (docs/prereg/PREREG_GRL.md) — plain RL on
# Qwen3-8B's quick grid translation for one cross-fitting fold (vLLM with LoRA slots on the server GPU for the rollouts, poc/gp_train.py on the
# trainer GPU, programs run in the sandbox python $P), then arm gtr with the final adapter on the fold's held-out test puzzles
# ($POC_DATA/grid_rl/fold<f>_ids.txt), GridPuzzle and Mitra-Baral, seeds 4-9, tag q8bgrl<f> (a server serving the adapter as "local").
# Needs PORT, P, POC_DATA, HF_HOME, VLLM_CACHE_ROOT as the other lanes set them. GRL_SKIP_TRAIN=1: the evaluation only; GRL_NO_EVAL=1: the training only.
out=$1 F=$2 GS=$3 GT=$4; shift 4
# GRL_NAME (PREREG_GRLLF): the run's name instead of grl<f> (tag q8b<name>, logs run_<name>_*.log); fold "all" is evaluated on all_ids.txt.
# GRL_BASE / GRL_TAGP / GRL_SEEDS (PREREG_GRLX): another model (passed to gp_train.py as --base), its tag prefix (q8b when unset), the evaluated seeds (4-9).
base=${GRL_BASE:-/SSD/huggingface/Qwen/Qwen3-8B} name=${GRL_NAME:-grl$F} ids=$POC_DATA/grid_rl/fold${F}_ids.txt tp=${GRL_TAGP-q8b}
[ "$F" = all ] && ids=$POC_DATA/grid_rl/all_ids.txt
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
mkdir -p $out
if [ -z "$GRL_SKIP_TRAIN" ]; then
  S=$(bash poc/start_server.sh $base $PORT $GS 0.85 ${name}_train --max-model-len 8192 --enable-lora --max-lora-rank 16 --max-loras 2 \
    --max-num-seqs 256) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  POC_PYTHON=$P CUDA_VISIBLE_DEVICES=$GT PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /opt/conda/bin/python poc/gp_train.py $out $F --base $base "$@" >> results/run_${name}_train.log 2>&1
  kill $S; sleep 15
fi
[ -n "$GRL_NO_EVAL" ] && exit 0
[ -d $out/adapter_final ] || { echo "no adapter_final in $out" >> results/run_${name}_train.log; exit 1; }
S=$(bash poc/start_server.sh $base $PORT $GS 0.85 ${name}_eval --max-model-len 20480 --served-model-name base --enable-lora \
  --max-lora-rank 16 --max-loras 1 --lora-modules local=$out/adapter_final) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in ${GRL_SEEDS:-4 5 6 7 8 9}; do
  $P poc/run_zebra.py --gp $tp$name gtr $s --ids $ids >> results/run_${name}_eval.log 2>&1 &
  $P poc/run_zebra.py --gp $tp$name gtr $s --set lgp --ids $ids >> results/run_${name}_eval.log 2>&1 &
done
wait
kill $S; sleep 10
echo "GRL $name fold $F done $(date -u)" >> results/run_${name}_eval.log
