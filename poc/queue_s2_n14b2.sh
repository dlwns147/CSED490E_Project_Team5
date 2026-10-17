#!/bin/bash
# N14b addendum: gpt-oss-20b low on 8043 GPU0.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8043 0 0.88 n14b2) || exit 1
export POC_BASE_URL=http://127.0.0.1:8043/v1 POC_REASONING_EFFORT=low
CX="--arms solver --n_inst 4 --temperature 0.7 --fmt_fix --api_doc --api_doc_task --max_tokens 16000 --probs vrptw"
MIN="Change as few lines as possible: keep every line that is unrelated to the new rule exactly as it is"
for sd in 1 2 3; do
  $P poc/run_co.py --model_tag S2_N14b_oss20_vrptw_adsnipmin_s$sd $CX --seed $sd --adapt_from results/n14/src_S2_N10m2_cvrp_good.py \
    --adapt_note "solves a related problem (capacitated vehicle routing without time windows). $MIN" > results/run_S2_N14b_oss20_s$sd.log 2>&1 &
  [ $sd -gt 1 ] && $P poc/run_co.py --model_tag S2_N14b_oss20_snip_s$sd $CX --seed $sd > results/run_S2_N14b_oss20_snip_s$sd.log 2>&1 &
done; wait
kill $S
echo "S2_N14b2 runs done $(date)" >> results/queue_log.txt
