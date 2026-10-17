#!/bin/bash
# F3y (FINDINGS pre-registration): unambiguous VRPTW header, gpt-oss low, exact snippet, prose only. 8042 = 120b, 8043 = 20b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
C="--arms solver --probs vrptw --n_inst 15 --repair 2 --temperature 0.7 --max_tokens 16000 --api_doc --api_doc_task --fmt_fix"
for sd in 1 2; do
  ( export POC_BASE_URL=http://127.0.0.1:8042/v1 POC_REASONING_EFFORT=low; $P poc/run_co.py --model_tag S2_F3y_cooss120low_vrptw_fmtfix_s$sd $C --seed $sd > results/run_S2_F3y_120_s$sd.log 2>&1 ) &
  ( export POC_BASE_URL=http://127.0.0.1:8043/v1 POC_REASONING_EFFORT=low; $P poc/run_co.py --model_tag S2_F3y_cooss20low_vrptw_fmtfix_s$sd $C --seed $sd > results/run_S2_F3y_20_s$sd.log 2>&1 ) &
done
wait
echo "S2_F3y done $(date)" >> results/queue_log.txt
