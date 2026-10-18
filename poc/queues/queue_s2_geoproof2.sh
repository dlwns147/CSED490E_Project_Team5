#!/bin/bash
# PROOF phase 3a addendum: Qwen3.6 thinking proposes auxiliary points for the 18 IMO-AG-30 problems DD+AR cannot prove alone; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_2 || exit 1
S=$(bash poc/start_server.sh /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8085 2 0.88 geoproof_q36 --max-num-seqs 64 --language-model-only --max-model-len 36000) && {
  POC_TIMEOUT=7200 POC_THINK_SAMPLING=temperature=1.0,top_p=0.95,top_k=20 POC_BASE_URL=http://127.0.0.1:8085/v1 $P poc/geoproof_gen.py q36_think 16 --think --max_tokens 30000 >> results/geoproof/run_q36_think.log 2>&1
  kill $S; sleep 20; }
rmdir results/.gpu_claim_2
echo "S2_GEOPROOF q36_think proposals done $(date)" >> results/queue_log.txt
cd /SSD/lean_postech/ag && nice -n 10 venv/bin/python ddar_aux.py /NAS/SJ/POSTECH/nlp/results/geoproof/aux_q36_think.jsonl 600 >> /NAS/SJ/POSTECH/nlp/results/geoproof/run_q36_think.log 2>&1
echo "S2_GEOPROOF q36_think checked by DD+AR $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
