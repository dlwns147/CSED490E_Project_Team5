#!/bin/bash
# CH (docs/prereg/PREREG_CH.md, 2026-10-19): approach hints on the 311 contest geometry problems. gpt-oss-120b on GPU1 (port 8044) and
# gpt-oss-20b on GPU2 (port 8045), medium effort, 16k as the existing medium runs; arms --tags and --plan, seeds 1-3 (new tags).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export CC_SET=full POC_TIMEOUT=7200
lane() { g=$1 port=$2 dir=$3 m=$4
  mkdir results/.gpu_claim_$g || return 1
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh /SSD/huggingface/openai/$dir $port $g 0.88 ch_${m}_$att) || { sleep 60; continue; }
    for sd in 1 2 3; do
      POC_REASONING_EFFORT=medium POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run ${m}_medium_tag $sd --tags --max_tokens 16000 >> results/h2/run_ch_${m}_tag_s$sd.log 2>&1 &
      POC_REASONING_EFFORT=medium POC_BASE_URL=http://127.0.0.1:$port/v1 $P poc/run_cc.py run ${m}_medium_plan $sd --plan --max_tokens 16000 >> results/h2/run_ch_${m}_plan_s$sd.log 2>&1 &
    done; wait
    kill $S; sleep 30
    n=$(cat results/h2/cc_full_${m}_medium_tag_s*.jsonl results/h2/cc_full_${m}_medium_plan_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 1698 ] && break
  done
  rmdir results/.gpu_claim_$g
  echo "S2_CH $m done ($n/1698) $(date)" >> results/queue_log.txt; }
echo "S2_CH started $(date)" >> results/queue_log.txt
lane 1 8044 gpt-oss-120b oss120 & sleep 60; lane 2 8045 gpt-oss-20b oss20 & wait
CC_SET=full $P poc/analyze_ch.py oss120 oss20 > results/h2/ch_analysis.log 2>&1
echo "S2_CH done (analysis: results/h2/ch_analysis.log) $(date)" >> results/queue_log.txt
