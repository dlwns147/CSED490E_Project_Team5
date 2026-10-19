#!/bin/bash
# ADAPT (docs/prereg/PREREG_X1.md addendum 2026-10-19): DeepSeek-R1-Distill-Qwen-7B (r1d7) and AdaptThink-7B (adt7) on X1 (MATH-500 + AIME 24/25),
# modes text / prog (NoThinking) and think, seeds 1-3; both servers on GPU1 (7B each), 16K context as in the AdaptThink paper.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
ready() { local d=$1; [ -f $d/model.safetensors.index.json ] || return 1
  for s in $(python3 -c "import json;print(' '.join(sorted(set(json.load(open('$d/model.safetensors.index.json'))['weight_map'].values()))))"); do [ -f $d/$s ] || return 1; done
  [ -z "$(find $d/.cache -name '*.incomplete' 2>/dev/null)" ]; }
M1=/SSD/huggingface/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B; M2=/SSD/huggingface/THU-KEG/AdaptThink-7B-delta0.05
for i in $(seq 360); do ready $M1 && ready $M2 && break; sleep 20; done
G=1; [ "$(nvidia-smi -i $G --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$G || exit 1
echo "S2_ADAPT started on GPU$G $(date)" >> results/queue_log.txt
lane() {   # lane <tag> <model> <port>
  local tag=$1 m=$2 port=$3
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh $m $port $G 0.44 ${tag}_$att --max-model-len 16384) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:$port/v1
    for md in text prog think; do for sd in 1 2 3; do $P poc/run_adapt.py $tag $md $sd >> results/x1/run_adapt_${tag}.log 2>&1 & done; wait; done
    kill $S; sleep 20
    n=$(cat results/x1/math_${tag}_{text,prog,think}_s{1,2,3}.jsonl 2>/dev/null | wc -l); [ "$n" -ge 5040 ] && break
  done
  echo "S2_ADAPT $tag done ($n/5040) $(date)" >> results/queue_log.txt
}
lane r1d7 $M1 8120 & sleep 90; lane adt7 $M2 8121 & wait
rmdir results/.gpu_claim_$G
$P poc/analyze_x1.py r1d7 adt7 > results/x1/analysis_adapt.log 2>&1
[ -f poc/analyze_adapt.py ] && $P poc/analyze_adapt.py >> results/x1/analysis_adapt.log 2>&1
echo "S2_ADAPT done $(date)" >> results/queue_log.txt
