#!/bin/bash
# CO1 on a dedicated Qwen3-8B server (GPU 0, :8004): 3 arms, thinking off then on; shut down when done
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-8B 8004 q8b_co) || { echo "server failed"; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8004/v1
$P poc/run_co.py --model_tag co8b --max_tokens 4096 > results/run_co8b.log 2>&1
$P poc/run_co.py --model_tag co8b_think --think --max_tokens 12000 > results/run_co8b_think.log 2>&1
kill $S
echo CO_DONE >> results/queue_co.log
