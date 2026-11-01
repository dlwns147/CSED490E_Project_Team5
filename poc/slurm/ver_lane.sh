#!/bin/bash
# poc/slurm/ver_lane.sh <name>: VER (docs/prereg/PREREG_VER.md) — Qwen3-8B as a verifier of passing word-problem programs. LoRA SFT on
# $POC_DATA/optmath_train/sft_ver_<name>.jsonl (poc/ver_build.py; DT's recipe, 1 epoch, data-parallel over the job's 4 GPUs with the target-only loss (--tail-loss: the full logits ran a 3090 out of memory, 10-31); if that
# fails, on GPUs 0-1 with the model split as td_lane.sh), merged to /SSD/huggingface/derived/Qwen3-8B-ver-<name>; then the base model
# (tag ver0) and the trained one (tag ver<name>) score the stored programs and the train-dev set (poc/ver_score.py), one server each.
#   sbatch -J ver_<name> -x n19,n22 --gres=gpu:4 --cpus-per-task=16 poc/slurm/job.sh "bash poc/slurm/ver_lane.sh <name>"
# poc/slurm/ver_lane.sh --selw <out dir> (one GPU): PREREG_LCM addendum SEL-W — train the within-question word verifier on VER's programs
# (wp_train.py --orm), then serve Qwen3-8B with VER's adapter (ver_v1) and every SEL-W adapter; the development fallback sets are scored
# by all of them and the untrained model (local), lcm_shift.py --sel-val-w chooses the checkpoint, local / ver_v1 / the choice score
# ob403 and MAMO, and lcm_shift.py --sel-w decides. SELW_SMOKE=1: 32 problems, 2 steps (1 epoch), prefix selwsmk, 30 target requests per name.
#   sbatch -J selw -x n19,n22,n24,n26 poc/slurm/job.sh "bash poc/slurm/ver_lane.sh --selw /NAS/SJ/POSTECH/nlp_data/cv/selw"
if [ "$1" = --selw ]; then
  out=$2 D=/NAS/SJ/POSTECH/nlp_data/optmath_train B=/SSD/huggingface/Qwen/Qwen3-8B
  if [ "${SELW_SMOKE:-0}" = 1 ]; then pre=selwsmk tr="--smoke 32 --epochs 1 --save 2" lim=30; else pre=selw tr="" lim=1000000000; fi
  [ -f $out/adapter_final/adapter_config.json ] || /opt/conda/bin/python poc/wp_train.py $out --orm $tr >> results/x3/run_${pre}_train.log 2>&1 \
    || exit 1
  mods="ver_v1=$D/td/adapter_ver_v1" names=""
  for d in $out/adapter_*; do n=${pre}_${d##*/adapter_}; mods="$mods $n=$d"; names="$names,$n"; done
  export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
  S=$(bash poc/start_server.sh $B $PORT 0 0.90 ${pre}_${SLURM_JOB_ID} --max-model-len 20480 --enable-lora --max-lora-rank 16 --max-loras 4 \
    --max-cpu-loras 16 --max-num-seqs 64 --lora-modules $mods) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1 SEL_REQ=sel_req_w.jsonl
  SEL_SSETS=optibench,bwor,logior,optmath /opt/conda/bin/python poc/score_conf.py sel local,ver_v1$names >> results/run_${pre}_score.log 2>&1 \
    || { kill $S; exit 1; }
  best=$(/opt/conda/bin/python poc/lcm_shift.py --sel-val-w local,ver_v1$names | tee -a results/lcm_${pre}_val.log \
    | sed -n 's/^\*\*\* SEL-W checkpoint[^:]*: //p')
  echo "[$pre $(date -u '+%F %T')] chosen: $best" >> results/run_${pre}_score.log
  SEL_SSETS=ob403,mamo CONF_LIMIT=$lim /opt/conda/bin/python poc/score_conf.py sel local,ver_v1,$best >> results/run_${pre}_score.log 2>&1
  /opt/conda/bin/python poc/lcm_shift.py --sel-w $best > results/lcm_${pre}.log 2>&1
  kill $S; sleep 10; exit 0
fi
name=$1
D=/NAS/SJ/POSTECH/nlp_data/optmath_train M=/SSD/huggingface/derived/Qwen3-8B-ver-$name B=/SSD/huggingface/Qwen/Qwen3-8B
L=results/x3/run_ver_${name}_train.log
if [ ! -f $M/config.json ]; then
  CUDA_VISIBLE_DEVICES=0,1,2,3 /opt/conda/bin/python -m torch.distributed.run --nproc_per_node 4 poc/sft_lora.py $B $D/sft_ver_$name.jsonl \
    $D/td/adapter_ver_$name $M --epochs 1 --tail-loss >> $L 2>&1 \
  || { echo "data-parallel training failed ($(date -u)); model split over GPUs 0-1" >> $L
       CUDA_VISIBLE_DEVICES=0,1 /opt/conda/bin/python poc/sft_lora.py $B $D/sft_ver_$name.jsonl $D/td/adapter_ver_$name $M --epochs 1 --tail-loss >> $L 2>&1 \
       || exit 1; }
fi
S0=$(bash poc/start_server.sh $B $PORT 0 0.92 ver0_$SLURM_JOB_ID --max-model-len 20480) || exit 1
S1=$(bash poc/start_server.sh $M $((PORT + 1)) 1 0.92 ver${name}_$SLURM_JOB_ID --max-model-len 20480) || exit 1
POC_BASE_URL=http://127.0.0.1:$PORT/v1 $P poc/ver_score.py ver0 $name >> results/x3/run_ver_score.log 2>&1 &
POC_BASE_URL=http://127.0.0.1:$((PORT + 1))/v1 $P poc/ver_score.py ver$name $name >> results/x3/run_ver_score.log 2>&1 &
wait
kill $S0 $S1; sleep 10
chown -R $(stat -c %u:%g /NAS/SJ/POSTECH/nlp) $D/td
