#!/bin/bash
# B4 (results/PREREG_B4.md). 8040 Qwen3-32B-AWQ, 8041 Llama-3.3-70B, 8042 gpt-oss-120b, 8043 gpt-oss-20b.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
C="--arms solver --repair 2 --temperature 0.7 --max_tokens 16000"
r() { port=$1 eff=$2 tag=$3; shift 3; ( export POC_BASE_URL=http://127.0.0.1:$port/v1; [ -n "$eff" ] && export POC_REASONING_EFFORT=$eff
      $P poc/run_co.py --model_tag $tag $C "$@" > results/run_$tag.log 2>&1 ); }
for sd in 1 2; do
  for mp in "q32b 8040" "l70 8041"; do
    set -- $mp; m=$1 port=$2
    for pr in "cvrp 10" "vrptw 15"; do
      set -- $pr; prob=$1 ni=$2
      r $port "" S2_B4_co${m}_${prob}_snippet_s$sd --probs $prob --n_inst $ni --seed $sd --api_doc --api_doc_task &
      r $port "" S2_B4_co${m}_${prob}_bm25top3_s$sd --probs $prob --n_inst $ni --seed $sd --rag_lib 3 &
      r $port "" S2_B4_co${m}_${prob}_droc_s$sd --probs $prob --n_inst $ni --seed $sd --droc &
    done
  done
  r 8042 low S2_B4_cooss120low_vrptw_restate_s$sd --probs vrptw --n_inst 15 --seed $sd --api_doc --api_doc_task --restate &
  r 8043 low S2_B4_cooss20low_vrptw_restate_s$sd --probs vrptw --n_inst 15 --seed $sd --api_doc --api_doc_task --restate &
done
wait
echo "S2_B4 runs done $(date)" >> results/queue_log.txt
