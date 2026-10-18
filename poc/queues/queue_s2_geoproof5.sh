#!/bin/bash
# GEO-J: gpt-oss-20b medium proposes auxiliary points for the 44 JGEX-AG-231 problems DD+AR cannot prove alone; GPU0.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_0 || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8092 0 0.88 geoproof_jgex_$att --max-model-len 36000) || { sleep 60; continue; }
  GEO_SET=jgex POC_REASONING_EFFORT=medium POC_TIMEOUT=7200 POC_BASE_URL=http://127.0.0.1:8092/v1 $P poc/geoproof_gen.py jgex_oss20_medium30k 8 --max_tokens 30000 >> results/geoproof/run_jgex_oss20.log 2>&1
  kill $S; sleep 20
  [ "$(wc -l < results/geoproof/aux_jgex_oss20_medium30k.jsonl)" -ge 352 ] && break
done
rmdir results/.gpu_claim_0
echo "S2_GEOPROOF5 jgex proposals done $(date)" >> results/queue_log.txt
cd /SSD/lean_postech/ag && nice -n 10 venv/bin/python ddar_aux.py /NAS/SJ/POSTECH/nlp/results/geoproof/aux_jgex_oss20_medium30k.jsonl 600 >> /NAS/SJ/POSTECH/nlp/results/geoproof/run_jgex_oss20.log 2>&1
echo "S2_GEOPROOF5 jgex checked by DD+AR $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
