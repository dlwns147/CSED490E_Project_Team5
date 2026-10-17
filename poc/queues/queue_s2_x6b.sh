#!/bin/bash
# X6 + addendum (results/PREREG_X3.md): verbal optimization (NL4OPT + IndustryOR), thinking with / without the API snippet.
# GPU0 Qwen3-32B thinkf; GPU2 Qwen3.6 mip/mipf/think/thinkf; GPU3 Qwen3-8B mip/mipf/think/thinkf; seeds 1-3; resumable, 4 attempts per lane.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { model=$1 port=$2 gpu=$3 tag=$4 tmt=$5 arms=$6 extra=$7
  want=$(( 345 * 3 * $(echo $arms | wc -w) ))
  for att in 1 2 3 4; do
    S=$(bash poc/start_server.sh $model $port $gpu 0.88 x6_${tag}_$att $extra) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1
    for md in $arms; do for sd in 1 2 3; do
      case $md in think*) fl="--think --max_tokens $tmt";; *) fl="--max_tokens 8192";; esac
      $P poc/run_nlopt.py $tag $md $sd $fl >> results/x3/run_${tag}_${md}_s$sd.log 2>&1 &
    done; done; wait
    kill $S; sleep 20
    n=$(for md in $arms; do cat results/x3/opt_${tag}_${md}_s*.jsonl 2>/dev/null; done | wc -l); [ "$n" -ge "$want" ] && break
  done
  echo "S2_X6 $tag done ($n/$want rows) $(date)" >> results/queue_log.txt; }
lane /SSD/huggingface/Qwen/Qwen3-32B-AWQ 8062 0 q32b 16000 "thinkf" "" &
lane /SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 8064 2 q36 30000 "mip mipf think thinkf" "--max-num-seqs 64 --language-model-only" &
lane /SSD/huggingface/Qwen/Qwen3-8B 8063 3 q8b 16000 "mip mipf think thinkf" "" &
wait
echo "S2_X6 runs done $(date)" >> results/queue_log.txt
