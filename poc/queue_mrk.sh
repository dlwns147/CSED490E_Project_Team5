#!/bin/bash
# S6 k-curve: tool-free geometry programs, T=0.7, seeds up to 5 for 1.7B/8B/14B/32B (MR-select offline over k = 1..5 samples)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {  # lane <model> <port> <tag> <short> <seeds...>
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4; shift 4
  for sd in "$@"; do
    [ -s results/geocross_geox${m}_base_t07s$sd.jsonl ] || $P poc/run_geo_cross.py --model_tag geox${m}_base_t07s$sd --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_base_t07s$sd.log 2>&1
  done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8076 q8b_mrk 8b 4 5; lane /SSD/huggingface/Qwen/Qwen3-1.7B 8077 q17_mrk 1_7b 1 2 3 4 5 ) & L1=$!
sleep 30
( lane /SSD/huggingface/Qwen/Qwen3-14B 8078 q14b_mrk 14b 3 4 5 ) & L2=$!
sleep 30
( lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8079 q32b_mrk 32b 4 5 ) & L3=$!
wait $L1 $L2 $L3
echo MRK_DONE >> results/queue_distract.log
