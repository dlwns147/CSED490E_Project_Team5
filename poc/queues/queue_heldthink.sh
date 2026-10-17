#!/bin/bash
# Thinking on the held-out CO problems (bin packing, vertex cover; 108 inst): does reasoning fix the remaining systematic bin-packing failures at 8B/14B?
# scoped snippet and full sheet, solver + 2 repairs, --think (20k), T=0.7 s1.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() { S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for v in "doctask:--api_doc_task" "doc:--api_doc"; do n=${v%%:*}; x=${v#*:}
    $P poc/run_co.py --model_tag HT_co${m}_${n}_s1 --arms solver $x --repair 2 --probs binpack,vcover --n_inst 18 --temperature 0.7 --seed 1 --think --max_tokens 20000 > results/run_HT_co${m}_${n}_s1.log 2>&1; done
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-8B 8093 q8b_hthink 8b & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-14B 8094 q14b_hthink 14b & L2=$!
wait $L1 $L2
echo HELDTHINK_DONE >> results/queue_log.txt
