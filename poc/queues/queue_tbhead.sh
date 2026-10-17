#!/bin/bash
# S4d mitigation by wording: K=8 related distractors with a 'use only if needed' header (vs 'should use'); K=0 too (14B wording sensitivity)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
lane() {
  S=$(start $1 $2 $3); export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$4
  for sd in 1 2; do for k in 0 8; do
    $P poc/run_geo_cross.py --model_tag geox${m}_dis${k}may_t07s$sd --distract $k --tb_head may --temperature 0.7 --seed $sd --max_tokens 4096 > results/run_geox${m}_dis${k}may_t07s$sd.log 2>&1
  done; done
  kill $S
}
( lane /SSD/huggingface/Qwen/Qwen3-8B 8065 q8b_tbh 8b; lane /SSD/huggingface/Qwen/Qwen3-14B 8066 q14b_tbh 14b ) & L1=$!
sleep 30
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8067 q32b_tbh 32b & L2=$!
wait $L1 $L2
echo TBHEAD_DONE >> results/queue_distract.log
