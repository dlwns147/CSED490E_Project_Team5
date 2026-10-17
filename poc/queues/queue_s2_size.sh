#!/bin/bash
# SIZE (docs/prereg/PREREG_SIZE.md + addendum): models that fit one RTX 3090 on the U1 suites and X6.
# One lane per model; each lane waits (<= 8 h) for a free GPU among 0-3 and claims it with mkdir (results/.gpu_claim_<g>).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter --resume"
CX="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --resume"
claim() { for i in $(seq 1440); do for g in 3 2 0 1; do
    [ "$(nvidia-smi -i $g --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$g 2>/dev/null && { echo $g; return 0; }
  done; sleep 20; done; return 1; }
lane() { dir=$1 tag=$2 port=$3 lo=$4 hi=$5   # lo / hi: POC_REASONING_EFFORT for the no-thinking / thinking arms (gpt-oss only)
  for i in $(seq 360); do [ -f "$dir/config.json" ] && break; sleep 20; done   # q14a: wait for its download
  G=$(claim) || { echo "S2_SIZE $tag: no free GPU within 8 h $(date)" >> results/queue_log.txt; return 1; }
  echo "S2_SIZE $tag started on GPU$G $(date)" >> results/queue_log.txt
  g() { t=S2_U1_${tag}_geo_$1; shift; $P poc/run_geo_cross.py --model_tag $t $GX "$@" >> results/run_$t.log 2>&1; }
  c() { t=S2_U1_${tag}_co_$1; shift; $P poc/run_co.py --model_tag $t $CX "$@" >> results/run_$t.log 2>&1; }
  o() { $P poc/run_nlopt.py $tag "$@" >> results/x3/run_${tag}_$1_s$2.log 2>&1; }
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $dir $port $G 0.88 size_${tag}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1
    export POC_REASONING_EFFORT=$lo; [ -z "$lo" ] && unset POC_REASONING_EFFORT
    for sd in 1 2 3; do
      g base_s$sd --seed $sd --distract 8 --logprobs --max_tokens 4096 & c base_s$sd --seed $sd --api_doc --logprobs --max_tokens 4096 &
      g fact_s$sd --seed $sd --distract 0 --algo_hint --max_tokens 4096 & c fact_s$sd --seed $sd --api_doc --api_doc_task --max_tokens 4096 &
      g decor_s$sd --seed $sd --max_tokens 4096 & c decor_s$sd --seed $sd --retrieve 3 --max_tokens 4096 &
      o mip $sd --max_tokens 8192 & o mipf $sd --max_tokens 8192 &
    done; wait
    export POC_REASONING_EFFORT=$hi; [ -z "$hi" ] && unset POC_REASONING_EFFORT
    for sd in 1 2 3; do
      g think_s$sd --seed $sd --distract 8 --think --max_tokens 16000 & c think_s$sd --seed $sd --api_doc --think --max_tokens 16000 &
      o think $sd --think --max_tokens 16000 & o thinkf $sd --think --max_tokens 16000 &
    done; wait
    kill $S; sleep 20
    n=$(cat results/x3/opt_${tag}_thinkf_s*.jsonl results/geocross_S2_U1_${tag}_geo_think_s*.jsonl 2>/dev/null | wc -l); [ "$n" -ge 1359 ] && break
  done
  rmdir results/.gpu_claim_$G
  echo "S2_SIZE $tag done ($n/1359 think rows) $(date)" >> results/queue_log.txt; }
lane /SSD/huggingface/Qwen/Qwen3-4B q4b 8069 "" "" &
lane /SSD/huggingface/Qwen/Qwen3-14B-AWQ q14a 8070 "" "" &
lane /SSD/huggingface/openai/gpt-oss-20b oss20 8071 low medium &
lane /SSD/huggingface/Qwen/Qwen3-1.7B q17 8068 "" "" &
wait
echo "S2_SIZE runs done $(date)" >> results/queue_log.txt
