#!/bin/bash
# N14c (PREREG_N14.md): job-shop + release dates. gpt-oss-120b low on 8043 GPU0; Qwen3-32B-AWQ on 8042 GPU2 (H5 programs first, then pick).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
rd() { tag=$1; shift; $P poc/run_jssp_rd.py run "$tag" "$@" > results/h5/rd/run_${tag}_$1.log 2>&1; }
( S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8043 0 0.88 n14c_o120) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8043/v1 POC_REASONING_EFFORT=low
  for i in $(seq 60); do [ -f results/h5/rd/src_oss120_low_plain_good.py ] && break; sleep 10; done
  for sd in 1 2; do
    rd oss120_scratch $sd --max_tokens 16000 &
    rd oss120_good $sd --max_tokens 16000 --adapt results/h5/rd/src_oss120_low_plain_good.py --note "solves job-shop scheduling without release dates" &
    [ -f results/h5/rd/src_oss120_low_plain_bad.py ] && rd oss120_bad $sd --max_tokens 16000 --adapt results/h5/rd/src_oss120_low_plain_bad.py --note "solves job-shop scheduling without release dates" &
    wait   # one seed at a time: the three conditions share the CPU load equally
  done
  kill $S ) &
( S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8042 2 0.88 n14c_q32b) || exit 1
  export POC_BASE_URL=http://127.0.0.1:8042/v1
  for sd in 1 2; do $P poc/run_jssp.py run q32b_plain $sd --max_tokens 8000 > results/h5/run_q32b_plain_s$sd.log 2>&1 & done; wait
  $P poc/run_jssp_rd.py pick q32b_plain > results/h5/rd/pick_q32b.log 2>&1
  for sd in 1 2; do
    rd q32b_scratch $sd --max_tokens 8000 &
    [ -f results/h5/rd/src_q32b_plain_good.py ] && rd q32b_good $sd --max_tokens 8000 --adapt results/h5/rd/src_q32b_plain_good.py --note "solves job-shop scheduling without release dates" &
    [ -f results/h5/rd/src_q32b_plain_bad.py ] && rd q32b_bad $sd --max_tokens 8000 --adapt results/h5/rd/src_q32b_plain_bad.py --note "solves job-shop scheduling without release dates" &
    wait   # one seed at a time: the three conditions share the CPU load equally
  done
  kill $S ) &
wait
echo "S2_N14c runs done $(date)" >> results/queue_log.txt
