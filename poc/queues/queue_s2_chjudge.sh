#!/bin/bash
# CH-P6 judge (docs/prereg/PREREG_CH.md): gpt-oss-120b low on GPU0 (port 8046) judges finished hint runs, repeatedly until S2_CH is done.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_REASONING_EFFORT=low
mkdir results/.gpu_claim_0 || exit 1
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8046 0 0.88 chjudge) || { rmdir results/.gpu_claim_0; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8046/v1
echo "S2_CHJUDGE started on GPU0 $(date)" >> results/queue_log.txt
for i in $(seq 40); do
  fin=$(grep -c "S2_CH done (analysis" results/queue_log.txt)
  for m in oss120 oss20; do $P poc/judge_ch.py $m >> results/h2/run_chjudge.log 2>&1; done
  [ "$fin" -ge 1 ] && break
  sleep 600
done
kill $S; sleep 20; rmdir results/.gpu_claim_0
echo "S2_CHJUDGE done $(date)" >> results/queue_log.txt
