#!/bin/bash
# PROOF phase 3b (docs/prereg/PREREG_PROOF.md): gpt-oss-20b medium, 30k cap, with and without the construction definitions; GPU0.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_0 || exit 1
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8086 0 0.88 geoproof_oss20b --max-model-len 36000) && {
  export POC_REASONING_EFFORT=medium POC_TIMEOUT=7200 POC_BASE_URL=http://127.0.0.1:8086/v1
  $P poc/geoproof_gen.py oss20_medium30k 16 --max_tokens 30000 >> results/geoproof/run_oss20_medium30k.log 2>&1 &
  $P poc/geoproof_gen.py oss20_defs30k 16 --max_tokens 30000 --defs >> results/geoproof/run_oss20_defs30k.log 2>&1 &
  wait; kill $S; sleep 20; }
rmdir results/.gpu_claim_0
echo "S2_GEOPROOF3 proposals done $(date)" >> results/queue_log.txt
cd /SSD/lean_postech/ag && for t in oss20_medium30k oss20_defs30k; do
  nice -n 10 venv/bin/python ddar_aux.py /NAS/SJ/POSTECH/nlp/results/geoproof/aux_$t.jsonl 600 >> /NAS/SJ/POSTECH/nlp/results/geoproof/run_$t.log 2>&1; done
echo "S2_GEOPROOF3 checked by DD+AR $(date)" >> /NAS/SJ/POSTECH/nlp/results/queue_log.txt
