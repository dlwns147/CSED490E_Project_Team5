#!/bin/bash
# LCM (docs/prereg/PREREG_LCM.md): the 31 cells of the derived-policy test, four per CPU job (one process each).
#   bash poc/slurm/lcm_cells.sh      -> results/lcm/<task>_<set>_<generator>_<peer>.json, logs results/lcm/run_<job>.log
cd "$(dirname "$0")/../.."
mkdir -p results/lcm
C=()
for s in dev fresh; do for gp in q8b:q35 q14a:q35 q35:q8b oss20:q35; do C+=("sql ${gp%%:*} ${gp##*:} $s"); done; done
for s in non-live live; do for gp in q8b:q35 q14a:q35 q35:q8b oss20:q35; do C+=("tc ${gp%%:*} ${gp##*:} $s"); done; done
for b in optibench bwor logior optmath; do for gp in q8b:oss20 q14a:q35 q35:q8b oss20:q35; do
  [ "$gp" = oss20:q35 ] && [ $b = optmath ] && continue; C+=("word ${gp%%:*} ${gp##*:} $b"); done; done
for ((j = 0; j < ${#C[@]}; j += 4)); do
  cmd=""
  for c in "${C[@]:j:4}"; do cmd+="python3 poc/lcm.py $c >> results/lcm/run_$((j / 4)).log 2>&1 & "; done
  sbatch -J lcm_$((j / 4)) -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none --cpus-per-task=4 poc/slurm/job.sh "${cmd}wait"
done
