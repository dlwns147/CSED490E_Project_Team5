#!/bin/bash
# 32B lane of queue_mmsol2, started directly on GPU 1 (the 8B server, started before the lock fix, still holds the pick lock)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
read F < <(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1)
[ "$F" -lt 20000 ] || { echo "GPU 1 busy ($F MiB)"; exit 1; }
S=$(poc/start_server.sh /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8040 1 0.45 q32b_mmsol2) || exit 1
export POC_BASE_URL=http://127.0.0.1:8040/v1
G="--games mastermind --code"
$P poc/run_games.py --model_tag mm32b_code_rep2 $G --code_repair 2 --max_tokens 4096 > results/run_games_mm32b_code_rep2.log 2>&1
$P poc/run_games.py --model_tag mm32b_code_think20k $G --think --code_repair 2 --max_tokens 20000 > results/run_games_mm32b_code_think20k.log 2>&1
kill $S
echo MMSOL2_32B_DONE >> results/queue_mmsol.log
