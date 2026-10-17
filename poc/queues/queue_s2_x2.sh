#!/bin/bash
# X2 (docs/prereg/PREREG_X2.md), restarted 18:29 without waiting for X1 (GPUs 0 and 2 were idle): GPU0 Qwen3-32B; GPU2 gpt-oss-20b, then Qwen3.6.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
echo "S2_X2 started $(date)" >> results/queue_log.txt
lane() { model=$1 port=$2 gpu=$3 tag=$4 eff=$5 extra=$6
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 x2_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1; if [ -n "$eff" ]; then export POC_REASONING_EFFORT=$eff; else unset POC_REASONING_EFFORT; fi
  $P poc/run_gsmsym.py $tag text > results/x2/run_${tag}_text.log 2>&1 & $P poc/run_gsmsym.py $tag solver > results/x2/run_${tag}_solver.log 2>&1 & wait
  $P poc/run_gsmsym.py --grade $tag > results/x2/grade_$tag.log 2>&1
  kill $S; sleep 20; }
mkdir -p results/x2
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8047 0 q32b "" "" &
( lane /SSD/huggingface/openai/gpt-oss-20b 8048 2 oss20 low ""; lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8048 2 q36 "" "--max-num-seqs 64 --language-model-only" ) &
wait
echo "S2_X2 runs done $(date)" >> results/queue_log.txt
