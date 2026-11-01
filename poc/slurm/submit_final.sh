#!/bin/bash
# FINAL (docs/prereg/PREREG_FINAL.md): SQL-1's arms on Spider's test split (SQL_SPLIT=spider, 2,147 questions; tags <model>sp), seeds
# 1-3, each model with the server settings of its BIRD runs (SQL-PA): Qwen3-8B on two GPUs (TP 2), Qwen3-14B-AWQ, Qwen3.5-9B with its
# card's thinking sampling, gpt-oss-20b as XG (low-effort N; medium-effort T and SB, harmony), and CV-1's trained quick query (C1
# adapter on Qwen3-8B, cheap arm only). Grading: `SQL_SPLIT=spider $P poc/grade_sql.py <tag> <seed>` at the end of each lane.
#   bash poc/slurm/submit_final.sh [seeds ...]
# TR (PREREG_LCM addendum TR): FINAL_SPLIT=spiderdev runs the same four generators on Spider's dev split (tags <model>sd, job names
# tr_*), without the trained adapter.
cd "$(dirname "$0")/../.."
X="-x n19,n22,n24,n26"
SP=${FINAL_SPLIT:-spider}; SPL=SQL_SPLIT=$SP
U=$([ "$SP" = spider ] && echo sp || echo sd); J=$([ "$SP" = spider ] && echo fin || echo tr)
for s in ${@:-1 2 3}; do
  sbatch -J ${J}_q8b_s$s $X --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/lane.sh --seq --gpus 0,1 \
    --vllm '--max-model-len 24576 --tensor-parallel-size 2' Qwen/Qwen3-8B ${J}_q8b_s$s "$SPL \$P poc/run_sql.py q8b$U $s" "$SPL \$P poc/grade_sql.py q8b$U $s"
  sbatch -J ${J}_q14a_s$s $X poc/slurm/job.sh poc/slurm/lane.sh --seq --vllm '--max-model-len 24576' Qwen/Qwen3-14B-AWQ ${J}_q14a_s$s \
    "$SPL \$P poc/run_sql.py q14a$U $s" "$SPL \$P poc/grade_sql.py q14a$U $s"
  sbatch -J ${J}_q35_s$s $X poc/slurm/job.sh "S=\$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.5-9B \$PORT 0 0.92 ${J}_q35_s$s --max-model-len 24576 --language-model-only --max-num-seqs 32) || exit 1; export POC_BASE_URL=http://127.0.0.1:\$PORT/v1 POC_TIMEOUT=7200 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20,presence_penalty=1.5 POC_BUDGET_CARD=1; $SPL \$P poc/run_sql.py q35$U $s >> results/sql/run_q35${U}_$s.log 2>&1; $SPL \$P poc/grade_sql.py q35$U $s >> results/sql/run_q35${U}_$s.log 2>&1; kill \$S"
  sbatch -J ${J}_oss20_s$s $X poc/slurm/job.sh poc/slurm/lane.sh --seq --vllm '--max-model-len 24576' openai/gpt-oss-20b ${J}_oss20_s$s \
    "$SPL POC_HARMONY=1 POC_REASONING_EFFORT=low SQL_ARMS=quick \$P poc/run_sql.py oss20$U $s" \
    "$SPL POC_HARMONY=1 POC_REASONING_EFFORT=medium SQL_ARMS=think,sb \$P poc/run_sql.py oss20$U $s" "$SPL \$P poc/grade_sql.py oss20$U $s"
done
[ "$SP" = spider ] && sbatch -J fin_c1 $X poc/slurm/job.sh "CV_EVAL_SPLIT=spider bash poc/slurm/cv_eval_lane.sh c1 q8bcvc1sp /NAS/SJ/POSTECH/nlp_data/cv/c1/adapter_final ${*:-1 2 3} && for s in ${*:-1 2 3}; do SQL_SPLIT=spider \$P poc/grade_sql.py q8bcvc1sp \$s; done >> results/sql/run_cv_eval_c1.log 2>&1"
