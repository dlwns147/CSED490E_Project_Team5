#!/bin/bash
# X1-SIZE (docs/prereg/PREREG_X1.md): Qwen3-4B / 8B / 14B-AWQ on MATH-500 + AIME, text / prog / think (28k), seeds 1-3. GPU0: q14a; GPU3: q8b, q4b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { gpu=$1; shift
  for spec in "$@"; do set -- $spec; dir=$1 tag=$2 port=$3
    for att in 1 2 3; do
      S=$(bash poc/start_server.sh $dir $port $gpu 0.88 x1size_${tag}_$att) || { sleep 60; continue; }
      export POC_BASE_URL=http://127.0.0.1:$port/v1
      for sd in 1 2 3; do
        $P poc/run_math.py $tag text $sd >> results/x1/run_${tag}_text_s$sd.log 2>&1 &
        $P poc/run_math.py $tag prog $sd >> results/x1/run_${tag}_prog_s$sd.log 2>&1 &
        $P poc/run_math.py $tag think $sd --think --max_tokens 28000 >> results/x1/run_${tag}_think_s$sd.log 2>&1 &
      done; wait
      kill $S; sleep 20
      n=$(cat results/x1/math_${tag}_*_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 5040 ] && break
    done
    echo "S2_X1SIZE $tag done ($n/5040 rows) $(date)" >> results/queue_log.txt
  done
  rmdir results/.gpu_claim_$gpu; }
mkdir results/.gpu_claim_0 results/.gpu_claim_3
lane 0 "/SSD/huggingface/Qwen/Qwen3-14B-AWQ q14a 8073" &
lane 3 "/SSD/huggingface/Qwen/Qwen3-8B q8b 8074" "/SSD/huggingface/Qwen/Qwen3-4B q4b 8075" &
wait
timeout 3600 $P poc/analyze_x1.py q4b q8b q14a > results/x1/analysis_size.log 2>&1
echo "S2_X1SIZE analysis -> results/x1/analysis_size.log $(date)" >> results/queue_log.txt
