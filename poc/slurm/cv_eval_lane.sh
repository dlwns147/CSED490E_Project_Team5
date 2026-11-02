#!/bin/bash
# poc/slurm/cv_eval_lane.sh <arm> <tag> <adapter dir> <seed> ...: CV-1's dev evaluation alone (cv_lane.sh's CV_EVAL step, same server)
# for an adapter already trained.
#   sbatch -J cv_eval_c1 -x n19,n22 poc/slurm/job.sh poc/slurm/cv_eval_lane.sh c1 q8bcvc1 /NAS/SJ/POSTECH/nlp_data/cv/c1/adapter_final 2 3
# poc/slurm/cv_eval_lane.sh orm <out dir>: PREREG_LCM addendum SEL — every adapter of the verifier training (and the untrained model,
# `local`) scores the fresh held-out-database candidates; the best adapter by that AUROC (lcm_shift.py --sel-val) and `local` then score the
# targets, and lcm_shift.py --sel decides. SEL_PREFIX names the adapters (default sel; the smoke: another prefix and SEL_LOCAL=0).
# poc/slurm/cv_eval_lane.sh orm-tc <out dir>: the same for addendum SEL-TC (held-out ToolACE for the choice, BFCL; prefix seltc).
# poc/slurm/cv_eval_lane.sh orm-tc-ab <out dir>: addendum SEL-AB2 — train the verifier with the no-call answer in every pool (tc_train.py
# --orm --abst, adapters every 150 steps), every adapter scores the held-out ToolACE AB sets (sel_req_abval.jsonl), lcm_shift.py
# --sel-val-ab chooses, the choice scores every AB text (sel_req_aball.jsonl), lcm_shift.py --sel-ab2 decides.
# poc/slurm/cv_eval_lane.sh pw <out dir>: addendum SEL-PW — train the pairwise verifier (cv_train.py pw on SEL's pool, copied), then every
# adapter and the untrained model (local) score the fresh held-out-database pairs (results/conf/sel_req_pw.jsonl, lcm_shift.py
# --sel-build-pw), lcm_shift.py --sel-val-pw chooses, the choice and local score the targets, lcm_shift.py --sel-pw decides.
# PW_SMOKE=1: 32 questions, 2 steps (1 epoch), prefix selpwsmk, 30 requests per name and set.
# poc/slurm/cv_eval_lane.sh pw-tc <out dir>: addendum SEL-PW-TC — the same on tool calls (tc_train.py --pw on SEL-TC's pool, adapters
# every 50 steps; held-out ToolACE for the choice without local, results/conf/sel_req_pwtc.jsonl from lcm_shift.py --sel-build-pwtc; BFCL
# with the choice and local; lcm_shift.py --sel-pwtc). PW_SMOKE=1: prefix selpwtcsmk.
#   sbatch -J selpw -x n19,n22,n24,n26 poc/slurm/job.sh "bash poc/slurm/cv_eval_lane.sh pw /NAS/SJ/POSTECH/nlp_data/cv/selpw"
if [ "$1" = pw ]; then
  out=$2
  if [ "${PW_SMOKE:-0}" = 1 ]; then pre=selpwsmk tr="--smoke 32 --epochs 1 --save 2" lim=30; else pre=selpw tr="" lim=1000000000; fi
  mkdir -p $out; [ -f $out/pool.jsonl ] || cp /NAS/SJ/POSTECH/nlp_data/cv/sel/pool.jsonl $out/ || exit 1
  [ -f $out/adapter_final/adapter_config.json ] || /opt/conda/bin/python poc/cv_train.py pw $out $tr >> results/sql/run_${pre}_train.log 2>&1 \
    || exit 1
  mods="" names=""
  for d in $out/adapter_*; do n=${pre}_${d##*/adapter_}; mods="$mods $n=$d"; names="$names,$n"; done
  export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0 0.90 ${pre}_${SLURM_JOB_ID} --max-model-len 16384 --enable-lora \
    --max-lora-rank 16 --max-loras 4 --max-cpu-loras 16 --max-num-seqs 64 --lora-modules $mods) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1 SEL_REQ=sel_req_pw.jsonl
  SEL_SSETS=fresh CONF_LIMIT=$lim /opt/conda/bin/python poc/score_conf.py sel local$names >> results/run_${pre}_score.log 2>&1 || { kill $S; exit 1; }
  best=$(/opt/conda/bin/python poc/lcm_shift.py --sel-val-pw local$names | tee -a results/lcm_${pre}_val.log \
    | sed -n 's/^\*\*\* SEL-PW checkpoint[^:]*: //p')
  echo "[$pre $(date -u '+%F %T')] chosen: $best" >> results/run_${pre}_score.log
  SEL_SSETS=dev,spider,spiderdev CONF_LIMIT=$lim /opt/conda/bin/python poc/score_conf.py sel $best,local >> results/run_${pre}_score.log 2>&1
  /opt/conda/bin/python poc/lcm_shift.py --sel-pw $best > results/lcm_${pre}.log 2>&1
  kill $S; sleep 10; exit 0
fi
if [ "$1" = pw-tc ]; then
  out=$2
  if [ "${PW_SMOKE:-0}" = 1 ]; then pre=selpwtcsmk tr="--smoke 32 --epochs 1 --save 2" lim=30; else pre=selpwtc tr="--save 50" lim=1000000000; fi
  mkdir -p $out
  [ -f $out/adapter_final/adapter_config.json ] || /opt/conda/bin/python poc/tc_train.py $out --pw $tr >> results/tc/run_${pre}_train.log 2>&1 \
    || exit 1
  mods="" names=""
  for d in $out/adapter_*; do n=${pre}_${d##*/adapter_}; mods="$mods $n=$d"; names="$names,$n"; done
  export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0 0.90 ${pre}_${SLURM_JOB_ID} --max-model-len 16384 --enable-lora \
    --max-lora-rank 16 --max-loras 4 --max-cpu-loras 16 --max-num-seqs 64 --lora-modules $mods) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1 SEL_REQ=sel_req_pwtc.jsonl
  SEL_SSETS=tcho CONF_LIMIT=$lim /opt/conda/bin/python poc/score_conf.py sel ${names#,} >> results/run_${pre}_score.log 2>&1 || { kill $S; exit 1; }
  best=$(/opt/conda/bin/python poc/lcm_shift.py --sel-val-pwtc ${names#,} | tee -a results/lcm_${pre}_val.log \
    | sed -n 's/^\*\*\* SEL-PW-TC checkpoint[^:]*: //p')
  echo "[$pre $(date -u '+%F %T')] chosen: $best" >> results/run_${pre}_score.log
  SEL_SSETS=bfcl CONF_LIMIT=$lim /opt/conda/bin/python poc/score_conf.py sel $best,local >> results/run_${pre}_score.log 2>&1
  /opt/conda/bin/python poc/lcm_shift.py --sel-pwtc $best > results/lcm_${pre}.log 2>&1
  kill $S; sleep 10; exit 0
fi
if [ "$1" = orm-tc-ab ]; then
  out=$2 pre=selab2
  mkdir -p $out
  [ -f $out/adapter_final/adapter_config.json ] || /opt/conda/bin/python poc/tc_train.py $out --orm --abst --save 150 \
    >> results/tc/run_${pre}_train.log 2>&1 || exit 1
  mods="" names=""
  for d in $out/adapter_*; do n=${pre}_${d##*/adapter_}; mods="$mods $n=$d"; names="$names,$n"; done
  names=${names#,}
  export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT 0 0.90 ${pre}_${SLURM_JOB_ID} --max-model-len 16384 --enable-lora \
    --max-lora-rank 16 --max-loras 4 --max-cpu-loras 16 --max-num-seqs 64 --lora-modules $mods) || exit 1
  export POC_BASE_URL=http://127.0.0.1:$PORT/v1
  SEL_REQ=sel_req_abval.jsonl SEL_SSETS=tcho /opt/conda/bin/python poc/score_conf.py sel $names >> results/run_${pre}_score.log 2>&1 \
    || { kill $S; exit 1; }
  best=$(/opt/conda/bin/python poc/lcm_shift.py --sel-val-ab $names | tee -a results/lcm_${pre}_val.log | sed -n 's/^\*\*\* SEL-AB2 checkpoint[^:]*: //p')
  echo "[$pre $(date -u '+%F %T')] chosen: $best" >> results/run_${pre}_score.log
  SEL_REQ=sel_req_aball.jsonl SEL_SSETS=tcho,bfcl /opt/conda/bin/python poc/score_conf.py sel $best >> results/run_${pre}_score.log 2>&1
  /opt/conda/bin/python poc/lcm_shift.py --sel-ab2 $best > results/lcm_${pre}.log 2>&1
  kill $S; sleep 10; exit 0
fi
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
