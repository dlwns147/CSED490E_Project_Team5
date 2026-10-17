#!/bin/bash
# F2R (docs/prereg/PREREG_F2R.md): gpt-oss-120b low (8043, GPU0) and Qwen3.8 no-think (8046, GPU1); helper round / ceil / roundwarn; seeds 1-2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { port=$1 eff=$2 tag=$3; shift 3; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
  for h in round ceil roundwarn; do for sd in 1 2; do
    $P poc/run_solomon.py run ${tag}_f2$h $sd --parser_int --helper $h "$@" > results/h3/run_${tag}_f2${h}_s$sd.log 2>&1; done; done ); }
S0=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8043 0 0.88 f2r_o120) && (lane 8043 low oss120_low --max_tokens 16000; kill $S0) &
S1=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.8-27B-FP8 8046 1 0.88 f2r_q38 --max-num-seqs 64 --language-model-only) && (lane 8046 "" q38 --max_tokens 16000; kill $S1) &
wait
echo "S2_F2R runs done $(date)" >> results/queue_log.txt
