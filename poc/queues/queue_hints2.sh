#!/bin/bash
# PoC F 2x2: tutor {8B, 32B} x student {1.7B, 8B}; identical hints across students of one tutor
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
T32=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8002 0 0.45 q32b_tutor) || { echo "32B failed"; exit 1; }
S17=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-1.7B 8001 2 0.25 q17b) || { echo "1.7B failed"; kill $T32; exit 1; }
TUTOR_URL=http://127.0.0.1:8002/v1 STUDENT_URL=http://127.0.0.1:8001/v1 $P poc/run_hints.py --tag t32b_s17b > results/run_hints_t32b_s17b.log 2>&1
kill $T32                                    # tutor no longer needed: free GPU 0
TUTOR_URL=http://127.0.0.1:8002/v1 STUDENT_URL=http://127.0.0.1:8000/v1 $P poc/run_hints.py --tag t32b_s8b --hints_from t32b_s17b > results/run_hints_t32b_s8b.log 2>&1 &
L1=$!
TUTOR_URL=http://127.0.0.1:8000/v1 STUDENT_URL=http://127.0.0.1:8000/v1 $P poc/run_hints.py --tag t8b_s8b --hints_from t8b_s17b > results/run_hints_t8b_s8b.log 2>&1 &
L2=$!
wait $L1 $L2
kill $S17
echo HINTS2_DONE >> results/queue_hints2.log
