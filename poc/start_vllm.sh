#!/bin/bash
# Old shared server only: on Slurm the job owns its GPU (index 0 inside the container); use poc/slurm/lane.sh instead.
# start_vllm.sh <model-dir> <tag>: pick the freest GPU, start vLLM on :8000, retry on a fresh pick if startup fails
# (e.g. a foreign job grew between the pick and vLLM's own free-memory check). Prints the server PID on success.
for attempt in 1 2 3 4 5 6; do
  read GPU FRAC < <(poc/pick_gpu.sh) || { echo "no GPU with >=30 GB free; waiting" >&2; sleep 120; continue; }
  echo "$2: attempt $attempt GPU $GPU frac $FRAC ($(date))" >> results/gpu_choice.log
  poc/serve_gpu.sh $1 8000 $GPU $FRAC > results/server_vllm_$2.log 2>&1 &
  SPID=$!
  while kill -0 $SPID 2>/dev/null; do curl -sf localhost:8000/health >/dev/null && { echo $SPID; exit 0; }; sleep 5; done
  echo "$2: startup failed on GPU $GPU: $(grep -m1 -oE 'ValueError: .{0,120}' results/server_vllm_$2.log)" >> results/gpu_choice.log
  sleep 60
done
exit 1
