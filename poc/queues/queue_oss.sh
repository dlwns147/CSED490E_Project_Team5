#!/bin/bash
# Review item 5 (model coverage): a third family, OpenAI gpt-oss (natively reasoning; effort low / medium), 20b on GPU 0, 120b on GPU 1.
# Core suite per model x effort, T=0.7 s1, max_tokens 16000 (reasoning counts toward it):
#  geometry main 5 tasks K0 / K8 ("should use", n=300); hard lattice/rectunion (no toolbox); lattice K0 signed helper (trap);
#  CO solver arm: 6 problems no doc / scoped snippet (n_inst 6 = 120 inst) and CVRP no doc / snippet (30 inst), repair 2.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
lane() { S=$(poc/start_server.sh $1 $2 $3 $4 $5) || { echo "$5 failed" >> results/queue_log.txt; return; }
  export POC_BASE_URL=http://127.0.0.1:$2/v1; m=$6
  for eff in low medium; do export POC_REASONING_EFFORT=$eff; t=${m}${eff:0:3}
    X="--stdlib --n_inst 30 --max_tokens 16000 --temperature 0.7 --seed 1"
    for k in 0 8; do $P poc/run_geo_cross.py --model_tag O5_geox${t}_k$k $X --distract $k > results/run_O5_geox${t}_k$k.log 2>&1; done
    $P poc/run_geo_cross.py --model_tag O5_geox${t}_hard $X --tasks lattice,rectunion > results/run_O5_geox${t}_hard.log 2>&1
    $P poc/run_geo_cross.py --model_tag O5_geox${t}_latk0 $X --tasks lattice --distract 0 > results/run_O5_geox${t}_latk0.log 2>&1
    C="--arms solver --repair 2 --temperature 0.7 --seed 1 --max_tokens 16000"
    $P poc/run_co.py --model_tag O5_co${t}_nodoc $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 6 > results/run_O5_co${t}_nodoc.log 2>&1
    $P poc/run_co.py --model_tag O5_co${t}_doctask $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 6 --api_doc --api_doc_task > results/run_O5_co${t}_doctask.log 2>&1
    $P poc/run_co.py --model_tag O5_coV${t}_nodoc $C --probs cvrp --n_inst 10 > results/run_O5_coV${t}_nodoc.log 2>&1
    $P poc/run_co.py --model_tag O5_coV${t}_doctask $C --probs cvrp --n_inst 10 --api_doc --api_doc_task > results/run_O5_coV${t}_doctask.log 2>&1
  done
  kill $S; }
lane /SSD/huggingface/openai/gpt-oss-20b 8062 0 0.45 gptoss20 oss20 & A=$!
sleep 30
lane /SSD/huggingface/openai/gpt-oss-120b 8063 1 0.88 gptoss120 oss120 & B=$!
wait $A $B
echo OSS_DONE >> results/queue_log.txt
