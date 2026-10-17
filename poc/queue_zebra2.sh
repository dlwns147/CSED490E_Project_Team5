#!/bin/bash
# PoC D zebra queue, restarted with lenient grid parsing; reuses the already-running servers (8B :8041 pid 955173,
# 32B :8042 pid 955982) and shuts them down at the end of each lane.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() {  # lane <port> <server-pid> <short>
  export POC_BASE_URL=http://127.0.0.1:$1/v1
  $P poc/run_zebra.py --model_tag z$3_nothink --max_tokens 4096 > results/run_zebra_z$3_nothink.log 2>&1
  $P poc/run_zebra.py --model_tag z$3_think --think --max_tokens 20000 > results/run_zebra_z$3_think.log 2>&1
  kill $2
}
lane 8041 955173 8b & L1=$!
lane 8042 955982 32b & L2=$!
wait $L1 $L2
echo ZEBRA_DONE >> results/queue_zebra.log
