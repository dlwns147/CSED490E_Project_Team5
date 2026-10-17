#!/bin/bash
# N18 (PREREG_N.md): Qwen3.6 no-think contest programs with raw log-probs, seeds 1-3 on GPUs 0-2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
lane() { port=$1 gpu=$2 sd=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 $port $gpu 0.88 n18_s$sd --max-num-seqs 64 --language-model-only) || return 1
  POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run q36_lp $sd --logprobs --max_tokens 28000 > results/h2/run_full_q36_lp_s$sd.log 2>&1
  kill $S; }
lane 8043 0 1 & lane 8044 1 2 & lane 8045 2 3 & wait
echo "S2_N18 runs done $(date)" >> results/queue_log.txt
