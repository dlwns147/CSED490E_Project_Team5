#!/bin/bash
# N14d(a) (PREREG_N14.md): minimal-edit instruction, Qwen3-32B-AWQ on 8042 GPU2: job-shop + release dates (seeds 1-2) and CVRP -> VRPTW
# with the time-window snippet (seeds 1-3).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8042 2 0.88 n14d_q32b) || exit 1
export POC_BASE_URL=http://127.0.0.1:8042/v1
MIN="Change as few lines as possible: keep every line that is unrelated to the new rule exactly as it is"
for sd in 1 2; do
  $P poc/run_jssp_rd.py run q32b_goodmin $sd --max_tokens 8000 --minimal --adapt results/h5/rd/src_q32b_plain_good.py \
    --note "solves job-shop scheduling without release dates" > results/h5/rd/run_q32b_goodmin_$sd.log 2>&1
done &
for sd in 1 2 3; do
  $P poc/run_co.py --model_tag S2_N14d_q32b_vrptw_adsnipmin_s$sd --arms solver --n_inst 4 --temperature 0.7 --fmt_fix --api_doc --api_doc_task \
    --max_tokens 8192 --probs vrptw --seed $sd --adapt_from results/n14/src_S2_N10_cvrp_good.py \
    --adapt_note "solves a related problem (capacitated vehicle routing without time windows). $MIN" > results/run_S2_N14d_q32b_vrptw_s$sd.log 2>&1 &
done
wait
kill $S
echo "S2_N14d runs done $(date)" >> results/queue_log.txt
