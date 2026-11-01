#!/bin/bash
# poc/slurm/vote_lane.sh (MT-V, docs/prereg/PREREG_MT.md addendum MT-V): two model servers in one job — the generator on GPU 0
# (port $PORT) and the peer on GPU 1 (port $PORT + 1) — then the client commands with POC_BASE_URL / POC_PEER_URL set:
#   sbatch -J mtv_q8b_s1 --gres=gpu:2 --cpus-per-task=8 poc/slurm/job.sh poc/slurm/vote_lane.sh Qwen/Qwen3-8B "<gen vllm args>" \
#     Qwen/Qwen3.5-9B "<peer vllm args>" mtv_q8b_s1 '<command>' ...
gen=$1 gargs=$2 peer=$3 pargs=$4 tag=$5; shift 5
S1=$(bash poc/start_server.sh /SSD/huggingface/$gen $PORT 0 0.92 ${tag}_gen $gargs) || exit 1
S2=$(bash poc/start_server.sh /SSD/huggingface/$peer $((PORT + 1)) 1 0.92 ${tag}_peer $pargs) || { kill $S1; exit 1; }
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 POC_PEER_URL=http://127.0.0.1:$((PORT + 1))/v1
for c in "$@"; do
  echo "[$tag $(date -u '+%F %T')] $c" >> results/run_$tag.log
  bash -c "$c" >> results/run_$tag.log 2>&1
done
kill $S1 $S2; sleep 15
echo "SL $tag done $(date -u)" >> results/queue_log.txt
