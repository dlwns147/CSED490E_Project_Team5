#!/bin/bash
# X2 solver re-run (the first solver runs crashed on int template ids; the text runs are valid). GPU2, models in sequence.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 tag=$2 eff=$3 extra=$4
  S=$(bash poc/start_server.sh $model 8052 2 0.88 x2b_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:8052/v1; if [ -n "$eff" ]; then export POC_REASONING_EFFORT=$eff; else unset POC_REASONING_EFFORT; fi
  $P poc/run_gsmsym.py $tag solver > results/x2/run_${tag}_solver.log 2>&1
  $P poc/run_gsmsym.py --grade $tag > results/x2/grade_$tag.log 2>&1
  kill $S; sleep 25; }
lane /SSD/huggingface/openai/gpt-oss-20b oss20 low ""
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b "" ""
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 q36 "" "--max-num-seqs 64 --language-model-only"
echo "S2_X2b (solver re-run) done $(date)" >> results/queue_log.txt
