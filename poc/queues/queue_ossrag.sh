#!/bin/bash
# gpt-oss-20b (low effort, GPU 1): does an incomplete or near-miss reference hurt a strong model? full cheat sheet and BM25 top-3 (near-miss)
# on the 6 problems (n_inst 6) and CVRP (30); compare with no doc / scoped snippet from queue_oss.sh.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8066 1 0.45 gptoss20_rag) || { echo "gptoss20_rag failed" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8066/v1 POC_REASONING_EFFORT=low
C="--arms solver --repair 2 --temperature 0.7 --seed 1 --max_tokens 16000"
$P poc/run_co.py --model_tag O5_cooss20low_doc $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 6 --api_doc > results/run_O5_cooss20low_doc.log 2>&1
$P poc/run_co.py --model_tag O5_cooss20low_ragt3 $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 6 --retrieve 3 > results/run_O5_cooss20low_ragt3.log 2>&1
$P poc/run_co.py --model_tag O5_coVoss20low_doc $C --probs cvrp --n_inst 10 --api_doc > results/run_O5_coVoss20low_doc.log 2>&1
$P poc/run_co.py --model_tag O5_coVoss20low_ragt3 $C --probs cvrp --n_inst 10 --retrieve 3 > results/run_O5_coVoss20low_ragt3.log 2>&1
kill $S
echo OSSRAG_DONE >> results/queue_log.txt
