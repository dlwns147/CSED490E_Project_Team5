#!/bin/bash
# SIZE-CC completion: the high64k seed-2 file had a NUL-filled line (torn write on the NAS) that made every resume crash, so 10 of 311
# problems were never generated. Finish them on the first free GPU, then run the pre-registered analysis.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
G=""; for i in $(seq 1440); do for g in 2 3 0 1; do
  [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$g 2>/dev/null && { G=$g; break 2; }; done; sleep 20; done
[ -n "$G" ] || exit 1
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8072 $G 0.88 sizecc_fix --max-model-len 65536) && {
  CC_SET=full POC_TIMEOUT=14400 POC_BASE_URL=http://127.0.0.1:8072/v1 POC_REASONING_EFFORT=high $P poc/run_cc.py run oss20_high64k 2 --max_tokens 62000 >> results/h2/run_oss20_high64k_s2.log 2>&1
  kill $S; sleep 20; }
rmdir results/.gpu_claim_$G
echo "S2_SIZECC fix: high64k s2 now $(wc -l < results/h2/cc_full_oss20_high64k_s2.jsonl)/311 rows $(date)" >> results/queue_log.txt
CC_SET=full N8_MODEL=oss20 N8_MEDIUM=medium64k timeout 1800 $P poc/analyze_n8.py > results/h2/sizecc_analysis.log 2>&1
echo "S2_SIZECC analysis -> results/h2/sizecc_analysis.log $(date)" >> results/queue_log.txt
