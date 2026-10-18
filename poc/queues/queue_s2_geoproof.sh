#!/bin/bash
# PROOF phase 3a (docs/prereg/PREREG_PROOF.md): gpt-oss-20b medium proposes auxiliary points for IMO-AG-30; DD+AR checks (CPU). GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_2 || exit 1
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8084 2 0.88 geoproof_oss20) && {
  POC_REASONING_EFFORT=medium POC_BASE_URL=http://127.0.0.1:8084/v1 $P poc/geoproof_gen.py oss20_medium 16 --max_tokens 16000 >> results/geoproof/run_oss20_medium.log 2>&1
  kill $S; sleep 20; }
rmdir results/.gpu_claim_2
echo "S2_GEOPROOF oss20_medium proposals done $(date)" >> results/queue_log.txt
cd /SSD/lean_postech/ag && nice -n 10 venv/bin/python ddar_aux.py /NAS/SJ/POSTECH/nlp/results/geoproof/aux_oss20_medium.jsonl 600 >> /NAS/SJ/POSTECH/nlp/results/geoproof/run_oss20_medium.log 2>&1
echo "S2_GEOPROOF oss20_medium checked by DD+AR $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
