#!/bin/bash
# Why is T1 solver-TSP 0 while CO1 solver-TSP (same instances) is .75-1.0? Hypothesis: T1's vaguer repair feedback.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8036 q32b_t1fb 9>&-) || exit 1
U=http://127.0.0.1:8036/v1
POC_BASE_URL=$U $P poc/run_co_meta.py --model_tag t1_32b_tsp_fbdetail --arms solver --probs tsp --fb_detail > results/run_t1_32b_tsp_fbdetail.log 2>&1
POC_BASE_URL=$U $P poc/run_co_meta.py --model_tag t1_32b_tsp_fbvague --arms solver --probs tsp > results/run_t1_32b_tsp_fbvague.log 2>&1
kill $S
echo T1FB_DONE >> results/queue_t1fb.log
