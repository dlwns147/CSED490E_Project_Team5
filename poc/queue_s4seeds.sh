#!/bin/bash
# S4 robustness: does task-matched > all-predicates > baseline hold under sampling (T=0.7, 3 seeds)? 8B and 32B lanes.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {  # lane <model> <port> <tag> <short> <max_tokens>
  S=$(start $1 $2 $3)
  for sd in 1 2 3; do
    for arm in base prims prims_task; do
      case $arm in base) X="";; prims) X="--primitives";; prims_task) X="--primitives --prims_task";; esac
      POC_BASE_URL=http://127.0.0.1:$2/v1 $P poc/run_geo_cross.py --model_tag geox$4_${arm}_t07s$sd $X --temperature 0.7 --seed $sd --max_tokens $5 > results/run_geox$4_${arm}_t07s$sd.log 2>&1
    done
  done
  kill $S
}
lane /SSD/huggingface/Qwen/Qwen3-8B 8025 q8b_s4seeds 8b 2048 & L1=$!
sleep 60
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8026 q32b_s4seeds 32b 4096 & L2=$!
wait $L1 $L2
echo S4SEEDS_DONE >> results/queue_s4seeds.log
