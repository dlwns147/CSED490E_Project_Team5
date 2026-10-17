#!/bin/bash
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
start() { while true; do S=$(poc/start_server_retry.sh $1 $2 $3 9>&-) && { echo $S; return 0; }; sleep 300; done; }
S=$(start /SSD/huggingface/Qwen/Qwen3-8B 8022 q8b_s2b)
POC_BASE_URL=http://127.0.0.1:8022/v1 $P poc/run_geo.py --model_tag geo8b_code_canonprompt --mode code --canon_prompt --max_tokens 2048 > results/run_geo8b_code_cp.log 2>&1
kill $S
echo S2B_DONE >> results/queue_s2b.log
