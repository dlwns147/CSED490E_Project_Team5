#!/bin/bash
# RE-RUN of queue_llamastd.sh: the first run (port 8088, 20:29-20:34) was contaminated, because a peer session's Qwen3-8B server bound the same port
# 20:30:26-20:31:40 (SO_REUSEPORT), splitting requests. This session uses ports 8040-8099 only; port checked free first.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
PORT=8091
ss -ltn "sport = :$PORT" | grep -q LISTEN && { echo "port $PORT busy"; exit 1; }
S=$(poc/start_server_retry.sh /SSD/huggingface/meta-llama/Llama-3.1-8B-Instruct $PORT llama8b_std2 9>&-) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1
# sanity: the server on this port must be serving the Llama weights
curl -s localhost:$PORT/v1/models | grep -q "Llama-3.1-8B" || { echo "wrong model on $PORT" >> results/gpu_choice.log; kill $S; exit 1; }
for t in "std:--stdlib" "std_prims_task:--stdlib --primitives --prims_task" "base:"; do n=${t%%:*}; x=${t#*:}
  $P poc/run_geo_cross.py --model_tag geoxllama8b_${n}_v2 $x --max_tokens 2048 > results/run_geoxllama8b_${n}_v2.log 2>&1; done
for sd in 1 2 3 4 5; do
  $P poc/run_geo_cross.py --model_tag geoxllama8b_std03v2_t07s$sd --stdlib --temperature 0.3 --seed $sd --max_tokens 2048 > results/run_geoxllama8b_std03v2_s$sd.log 2>&1
done
kill $S
echo LLAMASTD2_DONE >> results/queue_distract.log
