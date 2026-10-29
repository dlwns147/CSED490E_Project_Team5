#!/bin/bash
# SQL-DV runs (docs/prereg/PREREG_SQL.md, addendum SQL-DV): quick answers only (SQL_ARMS / TC_ARMS=quick), seeds 1-3, BIRD dev and
# BFCL. Views s (shuffle) and p (plan) of Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B; plain prompts of Llama-3.1-8B-Instruct, Llama-3.2-3B-Instruct
# and Qwen3-4B. One job per model and task type, all its runs against one server.
cd "$(dirname "$0")/../.."
cmds() {   # <tag prefix> <view or ""> -> six commands (two views or one plain) for SQL ($1 = sql) or tool calls ($1 = tc)
  local kind=$1 tag=$2; shift 2
  for v in "$@"; do
    for s in 1 2 3; do
      local t=$tag$( [ "$v" = shuffle ] && echo vs; [ "$v" = plan ] && echo vp )
      if [ "$kind" = sql ]; then
        echo "${v:+SQL_VIEW=$v }SQL_ARMS=quick SQL_POOL=32 \$P poc/run_sql.py $t $s >> results/sql/run_$t.log 2>&1"
      else
        echo "${v:+TC_VIEW=$v }TC_ARMS=quick \$P poc/run_tc.py $t $s >> results/tc/run_$t.log 2>&1"
      fi
    done
  done
}
for kind in sql tc; do
  mapfile -t C < <(cmds $kind q14a shuffle plan)
  sbatch -J sqldv_q14a_$kind -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 16384' Qwen/Qwen3-14B-AWQ sqldv_q14a_$kind "${C[@]}"
  mapfile -t C < <(cmds $kind q8b shuffle plan)
  sbatch -J sqldv_q8b_$kind -x n19,n22 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --gpus 0,1 --vllm '--max-model-len 16384 --tensor-parallel-size 2' Qwen/Qwen3-8B sqldv_q8b_$kind "${C[@]}"
  mapfile -t C < <(cmds $kind q35 shuffle plan)
  J=$(printf '%s & ' "${C[@]}")
  sbatch -J sqldv_q35_$kind -x n19,n22 poc/slurm/job.sh "S=\$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.5-9B \$PORT 0 0.92 sqldv_q35_$kind --max-model-len 16384 --language-model-only --max-num-seqs 32) || exit 1; export POC_BASE_URL=http://127.0.0.1:\$PORT/v1 POC_TIMEOUT=7200; $J wait; kill \$S"
  for pm in "l8 meta-llama/Llama-3.1-8B-Instruct" "l3 meta-llama/Llama-3.2-3B-Instruct" "q4b Qwen/Qwen3-4B"; do
    set -- $pm
    mapfile -t C < <(cmds $kind $1 "")
    sbatch -J sqldv_$1_$kind -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --vllm '--max-model-len 16384' $2 sqldv_$1_$kind "${C[@]}"
  done
done
