#!/bin/bash
# N15e (PREREG_N15.md): job-shop solver-library choice. One lane per GPU, one condition at a time.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 port=$2 gpu=$3 tag=$4 mt=$5 eff=$6 extra=$7
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 n15e_$tag $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  for L in none cpsat mip; do for sd in 1 2; do
    JSSP_LIB=$L $P poc/run_jssp.py run ${tag}_$L $sd --max_tokens $mt > results/h5/run_${tag}_${L}_s$sd.log 2>&1
  done; done
  kill $S; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8043 0 q32b 8000 "" "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 1 q36 8000 "" "--max-num-seqs 64 --language-model-only" &
lane /SSD/huggingface/openai/gpt-oss-20b 8044 2 oss20_low 16000 low "" &
lane /SSD/huggingface/openai/gpt-oss-120b 8046 3 oss120_low 16000 low "" &
wait
echo "S2_N15e runs done $(date)" >> results/queue_log.txt
