#!/bin/bash
# gpt-oss-20b at HIGH reasoning effort (GPU 3): geometry K0 / K8, hard tasks, lattice signed-helper trap (completes the effort axis low/medium/high)
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-20b 8064 3 0.45 gptoss20_high) || { echo "gptoss20_high failed" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8064/v1 POC_REASONING_EFFORT=high; t=oss20hig
X="--stdlib --n_inst 30 --max_tokens 24000 --temperature 0.7 --seed 1"
for k in 0 8; do $P poc/run_geo_cross.py --model_tag O5_geox${t}_k$k $X --distract $k > results/run_O5_geox${t}_k$k.log 2>&1; done
$P poc/run_geo_cross.py --model_tag O5_geox${t}_hard $X --tasks lattice,rectunion > results/run_O5_geox${t}_hard.log 2>&1
$P poc/run_geo_cross.py --model_tag O5_geox${t}_latk0 $X --tasks lattice --distract 0 > results/run_O5_geox${t}_latk0.log 2>&1
kill $S
echo OSSHIGH_DONE >> results/queue_log.txt
