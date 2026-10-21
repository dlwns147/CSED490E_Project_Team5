#!/bin/bash
# Old shared server only: on Slurm the job owns its GPU (index 0 inside the container); use poc/slurm/lane.sh instead.
# start_server_retry.sh <model-dir> <port> <tag>: pick the freest GPU (>=30 GB free, >=20 GB headroom), start vLLM,
# retry with a fresh pick up to 6 times. Starts are SERIALISED with a lock (pick + load until healthy), because a server
# that is still loading does not show its memory yet and two concurrent starts would pick the same GPU.
exec 9>/dev/shm/poc_gpu_pick.lock
flock 9
for attempt in 1 2 3 4 5 6; do
  read GPU FRAC < <(poc/pick_gpu.sh) || { echo "$3: no GPU with enough free memory ($(date))" >> results/gpu_choice.log; sleep 120; continue; }
  PID=$(poc/start_server.sh $1 $2 $GPU $FRAC $3) && { echo $PID; exit 0; }
  sleep 60
done
exit 1
