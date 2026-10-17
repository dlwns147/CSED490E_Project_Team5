#!/bin/bash
# gpt-oss-20b seed-2 replication (GPU 3): low / medium effort, geometry K0 / K8 (n=300), CO no doc / snippet (6 problems + CVRP).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8068 3 0.45 gptoss20_s2) || { echo "gptoss20_s2 failed" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8068/v1
for eff in low medium; do export POC_REASONING_EFFORT=$eff; t=oss20${eff:0:3}
  for k in 0 8; do $P poc/run_geo_cross.py --model_tag O5_geox${t}_k${k}_s2 --stdlib --n_inst 30 --max_tokens 16000 --temperature 0.7 --seed 2 --distract $k > results/run_O5_geox${t}_k${k}_s2.log 2>&1; done
  C="--arms solver --repair 2 --temperature 0.7 --seed 2 --max_tokens 16000"
  for c in nodoc doctask; do x=""; [ $c = doctask ] && x="--api_doc --api_doc_task"
    $P poc/run_co.py --model_tag O5_co${t}_${c}_s2 $C --probs knapsack,tsp,color,sched,binpack,vcover --n_inst 6 $x > results/run_O5_co${t}_${c}_s2.log 2>&1
    $P poc/run_co.py --model_tag O5_coV${t}_${c}_s2 $C --probs cvrp --n_inst 10 $x > results/run_O5_coV${t}_${c}_s2.log 2>&1
  done
done
kill $S
echo OSS20S2_DONE >> results/queue_log.txt
