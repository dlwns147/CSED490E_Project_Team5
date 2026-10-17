#!/bin/bash
# SIZE-CC (docs/prereg/PREREG_SIZE.md): gpt-oss-20b medium and high (62k cap) on 311 validated Codeforces geometry problems, seeds 1-3; GPU2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_TIMEOUT=14400
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8072 2 0.88 sizecc_$att --max-model-len 65536) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8072/v1
  for sd in 1 2 3; do
    POC_REASONING_EFFORT=medium $P poc/run_cc.py run oss20_medium64k $sd --max_tokens 62000 >> results/h2/run_oss20_medium64k_s$sd.log 2>&1 &
    POC_REASONING_EFFORT=high $P poc/run_cc.py run oss20_high64k $sd --max_tokens 62000 >> results/h2/run_oss20_high64k_s$sd.log 2>&1 &
  done; wait
  kill $S; sleep 20
  n=$(cat results/h2/cc_full_oss20_medium64k_s*.jsonl results/h2/cc_full_oss20_high64k_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 1866 ] && break
done
echo "S2_SIZECC done ($n/1866 rows) $(date)" >> results/queue_log.txt
N8_MODEL=oss20 N8_MEDIUM=medium64k timeout 1800 $P poc/analyze_n8.py > results/h2/sizecc_analysis.log 2>&1
echo "S2_SIZECC analysis -> results/h2/sizecc_analysis.log $(date)" >> results/queue_log.txt
