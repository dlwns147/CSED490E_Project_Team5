#!/bin/bash
# N14 third model (PREREG_N14.md addendum): gpt-oss-20b low, 16k cap, 8044 on GPU 1; waits (bounded) for its source programs.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
for i in $(seq 360); do [ -f results/n14/sources_S2_N10m2.json ] && break; sleep 20; done
[ -f results/n14/sources_S2_N10m2.json ] || { echo "N14m2: no sources $(date)" >> results/queue_log.txt; exit 1; }
CX="--arms solver --n_inst 4 --temperature 0.7 --fmt_fix --api_doc --max_tokens 16000"
S=$(bash poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8044 1 0.88 n14_oss20) || exit 1
export POC_BASE_URL=http://127.0.0.1:8044/v1 POC_REASONING_EFFORT=low
for sd in 1 2 3; do
  for pair in "tsp cvrp the TSP (one vehicle, no capacity)" "cvrp vrptw capacitated vehicle routing without time windows"; do
    set -- $pair; src=$1 dst=$2; shift 2; desc="$*"
    for c in good bad; do [ -f results/n14/src_S2_N10m2_${src}_$c.py ] && $P poc/run_co.py --model_tag S2_N14_oss20_${dst}_${c}_s$sd $CX --probs $dst --seed $sd \
      --adapt_from results/n14/src_S2_N10m2_${src}_$c.py --adapt_note "solves a related problem ($desc)" > results/run_S2_N14_oss20_${dst}_${c}_s$sd.log 2>&1 & done
    $P poc/run_co.py --model_tag S2_N14_oss20_${dst}_unrel_s$sd $CX --probs $dst --seed $sd --adapt_from results/n14/src_S2_N10m2_knapsack_good.py \
      --adapt_note "solves a different problem (0/1 knapsack)" > results/run_S2_N14_oss20_${dst}_unrel_s$sd.log 2>&1 &
  done
done; wait
kill $S
echo "S2_N14m2 runs done $(date)" >> results/queue_log.txt
