#!/bin/bash
# HO-N as a job array: task i runs line i+1 of poc/slurm/hon_specs.txt through hon_lane.sh.
#   sbatch -J hon -a 0-21%14 poc/slurm/job.sh poc/slurm/hon_array.sh
spec=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" poc/slurm/hon_specs.txt)
[ -n "$spec" ] || { echo "hon_array: no spec for task $SLURM_ARRAY_TASK_ID"; exit 1; }
exec bash poc/slurm/hon_lane.sh $spec
