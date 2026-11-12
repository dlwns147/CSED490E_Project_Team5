#!/bin/bash
# poc/slurm/ifprep_lane.sh <bench> [n] [GPU] [what]: IFRL2 (docs/prereg/PREREG_IFRL.md, amendment) — before training, Qwen3-8B writes its
# checker for every prompt of <bench> (poc/if_train.py --checkers), then n (4) base responses per prompt as training samples them (--sample),
# for the offline J of the check (--jstat, run afterwards where the graders' packages are). what: all (default), checkers or sample;
# IF_SHARD=k/K splits --sample over K lanes (own files, read together by --jstat). Needs PORT, P as poc/slurm/job.sh sets them.
B=$1 N=${2:-4} G=${3:-0} W=${4:-all}
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-8B $PORT $G 0.90 ifprep_$B$G --max-model-len 32768 --served-model-name local) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
[ $W = sample ] || $P poc/if_train.py --checkers $B >> results/run_ifprep_$B.log 2>&1
[ $W = checkers ] || $P poc/if_train.py --sample $B $N >> results/run_ifprep_$B.log 2>&1
kill $S; sleep 10
echo "IFPREP $B $W ${IF_SHARD:-} done $(date -u)" >> results/run_ifprep_$B.log
