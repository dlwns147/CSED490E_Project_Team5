#!/bin/bash
# P1 (docs/prereg/PREREG_P1.md): prompt rewording on contest geometry. gpt-oss-120b low 8043 GPU0 (para 1) / 8044 GPU1 (para 2);
# Qwen3.6 no-think 8045 GPU2 (para 1) / 8046 GPU3 (para 2).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full
lane() { model=$1 port=$2 gpu=$3 tag=$4 para=$5 mt=$6 eff=$7 extra=$8
  S=$(bash poc/start_server.sh $model $port $gpu 0.88 p1_${tag}_$para $extra) || return 1
  export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  for sd in 1 2 3; do $P poc/run_cc.py run ${tag}_para$para $sd --para $para --max_tokens $mt > results/h2/run_full_${tag}_para${para}_s$sd.log 2>&1 & done; wait
  kill $S; }
lane /SSD/huggingface/openai/gpt-oss-120b 8043 0 oss120_low 1 16000 low "" &
lane /SSD/huggingface/openai/gpt-oss-120b 8044 1 oss120_low 2 16000 low "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 2 q36 1 28000 "" "--max-num-seqs 64 --language-model-only" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8046 3 q36 2 28000 "" "--max-num-seqs 64 --language-model-only" &
wait
echo "S2_P1 runs done $(date)" >> results/queue_log.txt
