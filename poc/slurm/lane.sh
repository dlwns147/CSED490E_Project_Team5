#!/bin/bash
# poc/slurm/lane.sh: one model server on the allocated GPU + client commands against it = the Slurm form of one lane of an old
# queue script (poc/queues/*.sh claimed GPUs 0-3 of a shared server; here each lane is its own job). Run through job.sh:
#   sbatch -J ob_q8b poc/slurm/job.sh poc/slurm/lane.sh Qwen/Qwen3-8B ob_q8b \
#     'NLOPT_SET=optibench $P poc/run_nlopt.py q8b_optibench free 1 --max_tokens 8192' \
#     'NLOPT_SET=optibench $P poc/run_nlopt.py q8b_optibench thinkfree 1 --think --max_tokens 16000'
# (`python bench.py submit ...` writes such lines for the standard arms.)
# Arguments: [options] <model dir under /SSD/huggingface> <tag> <client command> ...
#   --vllm '<args>'  extra vLLM arguments (default --max-model-len 20480: every 24 GB model fits a 3090 with 16k-token thinking)
#   --frac F         GPU memory fraction (default 0.92)
#   --seq            run the commands one after another (default: all at once, as the queue scripts did)
# Each command runs in bash with POC_BASE_URL set and $P = the client / sandbox python; its output goes to results/run_<tag>.log.
VLLM="--max-model-len 20480" FRAC=0.92 SEQ=""
while [ "${1#--}" != "$1" ]; do
  case $1 in --vllm) VLLM=$2; shift 2 ;; --frac) FRAC=$2; shift 2 ;; --seq) SEQ=1; shift ;; *) echo "lane.sh: unknown option $1"; exit 1 ;; esac
done
dir=$1 tag=$2; shift 2
[ -n "$dir" ] && [ -n "$tag" ] && [ $# -ge 1 ] || { echo "usage: lane.sh [--vllm ARGS] [--frac F] [--seq] <model dir> <tag> <command> ..."; exit 1; }
S=$(bash poc/start_server.sh /SSD/huggingface/$dir $PORT 0 $FRAC $tag $VLLM) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
for c in "$@"; do
  echo "[$tag $(date -u '+%F %T')] $c" >> results/run_$tag.log
  if [ -n "$SEQ" ]; then bash -c "$c" >> results/run_$tag.log 2>&1; else bash -c "$c" >> results/run_$tag.log 2>&1 & fi
done; wait
kill $S; sleep 15
echo "SL $tag done $(date -u)" >> results/queue_log.txt
