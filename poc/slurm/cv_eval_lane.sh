#!/bin/bash
# poc/slurm/cv_eval_lane.sh <arm> <tag> <adapter dir> <seed> ...: CV-1's dev evaluation alone (cv_lane.sh's CV_EVAL step, same server)
# for an adapter already trained.
#   sbatch -J cv_eval_c1 -x n19,n22 poc/slurm/job.sh poc/slurm/cv_eval_lane.sh c1 q8bcvc1 /NAS/SJ/POSTECH/nlp_data/cv/c1/adapter_final 2 3
# poc/slurm/cv_eval_lane.sh orm <out dir>: PREREG_LCM addendum SEL — every adapter of the verifier training (and the untrained model,
# `local`) scores the fresh held-out-database candidates; the best adapter by that AUROC (lcm_shift.py --sel-val) and `local` then score the
# targets, and lcm_shift.py --sel decides. SEL_PREFIX names the adapters (default sel; the smoke: another prefix and SEL_LOCAL=0).
# poc/slurm/cv_eval_lane.sh orm-tc <out dir>: the same for addendum SEL-TC (held-out ToolACE for the choice, BFCL; prefix seltc).
if [ "$1" = orm-tc ]; then
  out=$2 pre=${SEL_PREFIX:-seltc}
  mods="" names=""
  for d in $out/adapter_*; do n=${pre}_${d##*/adapter_}; mods="$mods $n=$d"; names="$names,$n"; done
  [ "${SEL_LOCAL:-1}" = 1 ] && names="local$names" || names=${names#,}
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0 0.90 seltc_${SLURM_JOB_ID} --max-model-len 16384 --enable-lora \
    --max-lora-rank 16 --max-loras 4 --max-cpu-loras 16 --max-num-seqs 64 --lora-modules $mods) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1 SEL_REQ=sel_req_tc.jsonl
  SEL_SSETS=tcho /opt/conda/bin/python poc/score_conf.py sel $names >> results/run_${pre}_score.log 2>&1 || { kill $S; exit 1; }
  best=$(/opt/conda/bin/python poc/lcm_shift.py --sel-val-tc $names | tee -a results/lcm_${pre}_val.log | sed -n 's/^\*\*\* SEL-TC checkpoint[^:]*: //p')
  echo "[$pre $(date -u '+%F %T')] chosen: $best" >> results/run_${pre}_score.log
  [ "${SEL_LOCAL:-1}" = 1 ] && tn=$best,local || tn=$best
  SEL_SSETS=bfcl /opt/conda/bin/python poc/score_conf.py sel $tn >> results/run_${pre}_score.log 2>&1
  /opt/conda/bin/python poc/lcm_shift.py --sel-tc $best > results/lcm_${pre}.log 2>&1
  kill $S; sleep 10; exit 0
fi
if [ "$1" = orm ]; then
  out=$2 pre=${SEL_PREFIX:-sel}
  mods="" names=""
  for d in $out/adapter_*; do n=${pre}_${d##*/adapter_}; mods="$mods $n=$d"; names="$names,$n"; done
  [ "${SEL_LOCAL:-1}" = 1 ] && names="local$names" || names=${names#,}
  export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0 0.90 sel_${SLURM_JOB_ID} --max-model-len 12288 --enable-lora \
    --max-lora-rank 16 --max-loras 4 --max-cpu-loras 16 --max-num-seqs 64 --lora-modules $mods) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  SEL_SSETS=fresh /opt/conda/bin/python poc/score_conf.py sel $names >> results/run_${pre}_score.log 2>&1 || { kill $S; exit 1; }
  best=$(/opt/conda/bin/python poc/lcm_shift.py --sel-val $names | tee -a results/lcm_${pre}_val.log | sed -n 's/^\*\*\* SEL checkpoint[^:]*: //p')
  echo "[$pre $(date -u '+%F %T')] chosen: $best" >> results/run_${pre}_score.log
  [ "${SEL_LOCAL:-1}" = 1 ] && tn=$best,local || tn=$best
  SEL_SSETS=dev,spider,spiderdev /opt/conda/bin/python poc/score_conf.py sel $tn >> results/run_${pre}_score.log 2>&1
  /opt/conda/bin/python poc/lcm_shift.py --sel $best > results/lcm_${pre}.log 2>&1
  kill $S; sleep 10; exit 0
fi
arm=$1 tag=$2 adapter=$3; shift 3
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
S=$(bash poc/start_server.sh ${CV_BASE:-/SSD/huggingface/Qwen/Qwen3-8B} $PORT 0 0.90 cv_eval_${arm}_${SLURM_JOB_ID} --max-model-len 8192 --enable-lora \
  --max-lora-rank 16 --max-loras 2 --max-num-seqs 128) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for s in "$@"; do /opt/conda/bin/python poc/cv_eval.py $arm $tag $adapter $s >> results/sql/run_cv_eval_${arm}.log 2>&1; done
kill $S; sleep 10
