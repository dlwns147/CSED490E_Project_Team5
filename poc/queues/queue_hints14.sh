#!/bin/bash
# PoC F: complete the tutor-student gap curve with a 14B student (hints reused from the 32B and 8B tutors; only the student is served)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-14B 8056 q14b_hints 9>&-) || exit 1
U=http://127.0.0.1:8056/v1
TUTOR_URL=$U STUDENT_URL=$U $P poc/run_hints.py --tag t32b_s14b --hints_from t32b_s17b > results/run_hints_t32b_s14b.log 2>&1
TUTOR_URL=$U STUDENT_URL=$U $P poc/run_hints.py --tag t8b_s14b --hints_from t8b_s17b > results/run_hints_t8b_s14b.log 2>&1
kill $S
echo HINTS14_DONE >> results/queue_hints14.log
