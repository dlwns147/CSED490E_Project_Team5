#!/bin/bash
# U2 (PREREG_U1.md): geometry with the K8 toolbox + a BM25-retrieved algorithm note, seeds 1-3; models one after another on GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
GX="--stdlib --n_inst 6 --temperature 0.7 --tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter --resume"
for spec in "/SSD/huggingface/Qwen/Qwen3-8B q8b" "/SSD/huggingface/Qwen/Qwen3-32B-AWQ q32b" "/SSD/huggingface/Qwen/Qwen3.6-35B-A3B-FP8 q36"; do
  set -- $spec; model=$1 tag=$2; extra=""; [ $tag = q36 ] && extra="--max-num-seqs 64 --language-model-only"
  S=$(bash poc/start_server.sh $model 8057 3 0.88 u2_$tag $extra) || continue
  export POC_BASE_URL=http://127.0.0.1:8057/v1
  for sd in 1 2 3; do t=S2_U1_${tag}_geo_retr_s$sd; $P poc/run_geo_cross.py --model_tag $t $GX --seed $sd --distract 8 --hint_retrieve --max_tokens 8192 >> results/run_$t.log 2>&1 & done; wait
  kill $S; sleep 20
done
echo "S2_U2 runs done $(date)" >> results/queue_log.txt
