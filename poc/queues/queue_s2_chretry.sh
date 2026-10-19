#!/bin/bash
# CH-R (docs/prereg/PREREG_CH.md addendum, 2026-10-19): fresh gpt-oss-20b medium samples (seeds 4-8, 16k, same prompt as seeds 1-3) to test
# "retry at medium with the free check instead of high effort" on samples not used to find it. GPU1: seeds 4-6, GPU2: seeds 7-8.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_TIMEOUT=7200 POC_REASONING_EFFORT=medium
lane() { g=$1 port=$2; shift 2
  mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b $port $g 0.88 chr_${g}_$att) || { sleep 60; continue; }
    for sd in "$@"; do POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run oss20_medium $sd --max_tokens 16000 >> results/h2/run_chr_s$sd.log 2>&1 & done; wait
    kill $S; sleep 30
    ok=1; for sd in "$@"; do [ "$(wc -l < results/h2/cc_full_oss20_medium_s$sd.jsonl)" -ge 311 ] || ok=0; done; [ $ok = 1 ] && break
  done
  rmdir results/.gpu_claim_$g; echo "S2_CHR lane GPU$g done (seeds $*) $(date)" >> results/queue_log.txt; }
echo "S2_CHR started $(date)" >> results/queue_log.txt
lane 1 8044 4 5 6 & sleep 30; lane 2 8045 7 8 & wait
echo "S2_CHR done $(date)" >> results/queue_log.txt
