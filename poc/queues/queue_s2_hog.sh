#!/bin/bash
# HO-G (docs/prereg/PREREG_HOG.md): held-out geometry tasks overlap / convex / tri / clip; U1 arms; GPUs 0 / 1 / 2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 12 --temperature 0.7 --tasks overlap,convex,tri,clip --resume"
lane() { g=$1 port=$2 dir=$3 tag=$4 lo=$5 hi=$6
  mkdir results/.gpu_claim_$g || return 1
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir $port $g 0.88 hog_$tag) || { rmdir results/.gpu_claim_$g; return 1; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1
  r() { t=S2_HOG_${tag}_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $t $GX "$@" >> results/run_$t.log 2>&1; }
  export POC_REASONING_EFFORT=$lo; [ -z "$lo" ] && unset POC_REASONING_EFFORT
  for sd in 1 2 3; do r base_s$sd --seed $sd --distract 8 --max_tokens 4096 & r fact_s$sd --seed $sd --distract 0 --algo_hint --max_tokens 4096 & done; wait
  export POC_REASONING_EFFORT=$hi; [ -z "$hi" ] && unset POC_REASONING_EFFORT
  for sd in 1 2 3; do r think_s$sd --seed $sd --distract 8 --think --max_tokens 16000 & done; wait
  kill $S; sleep 20; rmdir results/.gpu_claim_$g; echo "S2_HOG $tag done $(date)" >> results/queue_log.txt; }
echo "S2_HOG started $(date)" >> results/queue_log.txt
lane 0 8139 openai/gpt-oss-20b oss20 low medium & sleep 20
lane 1 8140 Qwen/Qwen3-14B-AWQ q14a "" "" & sleep 20
lane 2 8141 Qwen/Qwen3-8B q8b "" "" & wait
echo "S2_HOG done $(date)" >> results/queue_log.txt
