#!/bin/bash
# prints "<gpu-id> <mem-fraction>": the GPU with the most free memory, and a vLLM fraction that leaves >=20 GB headroom
# for the other containers' jobs (capped at 0.45 = 36 GB). Exits 1 if no GPU has >=30 GB free.
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits |
  awk -F', ' '{free=$3-$2; if (free>best) {best=free; id=$1; tot=$3}} END {
    if (best < 30000) exit 1;
    f=(best-20000)/tot; if (f>0.45) f=0.45; printf "%s %.2f\n", id, f }'
