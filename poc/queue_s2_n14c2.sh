#!/bin/bash
# N14c addendum: job-shop + release dates for gpt-oss-20b low (8044 GPU1) and Qwen3.6-35B-A3B no-think (8045 GPU0).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
rd() { tag=$1; shift; $P poc/run_jssp_rd.py run "$tag" "$@" > results/h5/rd/run_${tag}_$1.log 2>&1; }
NOTE="solves job-shop scheduling without release dates"
( S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8044 1 0.88 n14c_o20) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8044/v1 POC_REASONING_EFFORT=low
  $P poc/run_jssp_rd.py pick oss20_low_plain > results/h5/rd/pick_oss20.log 2>&1
  for sd in 1 2; do
    rd oss20_scratch $sd --max_tokens 16000 &
    rd oss20_good $sd --max_tokens 16000 --adapt results/h5/rd/src_oss20_low_plain_good.py --note "$NOTE" &
    [ -f results/h5/rd/src_oss20_low_plain_bad.py ] && rd oss20_bad $sd --max_tokens 16000 --adapt results/h5/rd/src_oss20_low_plain_bad.py --note "$NOTE" &
    wait
  done
  kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8045 0 0.88 n14c_q36 --max-num-seqs 64 --language-model-only) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8045/v1
  for sd in 1 2; do $P poc/run_jssp.py run q36_plain $sd --max_tokens 8000 > results/h5/run_q36_plain_s$sd.log 2>&1 & done; wait
  $P poc/run_jssp_rd.py pick q36_plain > results/h5/rd/pick_q36.log 2>&1
  for sd in 1 2; do
    rd q36_scratch $sd --max_tokens 8000 &
    [ -f results/h5/rd/src_q36_plain_good.py ] && rd q36_good $sd --max_tokens 8000 --adapt results/h5/rd/src_q36_plain_good.py --note "$NOTE" &
    [ -f results/h5/rd/src_q36_plain_bad.py ] && rd q36_bad $sd --max_tokens 8000 --adapt results/h5/rd/src_q36_plain_bad.py --note "$NOTE" &
    wait
  done
  kill $S ) &
wait
echo "S2_N14c2 runs done $(date)" >> results/queue_log.txt
