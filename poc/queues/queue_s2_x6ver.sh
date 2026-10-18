#!/bin/bash
# X6-VER (docs/prereg/PREREG_X3.md): a check-passing program of the same model for a similar problem of the other benchmark as the fact.
# usage: bash queue_s2_x6ver.sh <gpu> <model dir> <tag> <port> <think cap> [extra server args]   (mip_s1 rows of <tag> must exist)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
g=$1 dir=$2 tag=$3 port=$4 tmt=$5; shift 5; extra="$*"
mkdir results/.gpu_claim_$g || exit 1
for att in 1 2 3; do
  S=$(bash poc/start_server.sh $dir $port $g 0.88 x6ver_${tag}_$att $extra) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1 POC_TIMEOUT=14400
  for sd in 1 2 3; do
    $P poc/run_nlopt.py $tag mipv $sd --max_tokens 8192 >> results/x3/run_${tag}_mipv_s$sd.log 2>&1 &
    $P poc/run_nlopt.py $tag thinkv $sd --think --max_tokens $tmt >> results/x3/run_${tag}_thinkv_s$sd.log 2>&1 &
  done; wait
  kill $S; sleep 20
  n=$(cat results/x3/opt_${tag}_mipv_s*.jsonl results/x3/opt_${tag}_thinkv_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 2070 ] && break
done
rmdir results/.gpu_claim_$g
echo "S2_X6VER $tag done ($n/2070) $(date)" >> results/queue_log.txt
