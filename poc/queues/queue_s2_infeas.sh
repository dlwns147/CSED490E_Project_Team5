#!/bin/bash
# INFEAS (docs/prereg/PREREG_X7.md, 2026-10-19): one repair turn for programs that printed 'No Best Solution' (GPU2; 3090-class models).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
G=2; [ "$(nvidia-smi -i $G --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$G || exit 1
echo "S2_INFEAS started on GPU$G $(date)" >> results/queue_log.txt
for spec in "openai/gpt-oss-20b oss20 low" "Qwen/Qwen3-14B-AWQ q14a" "Qwen/Qwen3-8B q8b"; do
  set -- $spec; dir=$1 m=$2 eff=$3
  for att in 1 2 3; do
    S=$(bash poc/start_server.sh /SSD/huggingface/$dir 8123 $G 0.88 infeas_${m}_$att) || { sleep 60; continue; }
    export POC_BASE_URL=http://127.0.0.1:8123/v1 POC_REASONING_EFFORT=$eff NLOPT_EX_TAG=$m
    for sd in 1 2 3; do
      NLOPT_SET=mamo $P poc/run_infeas.py ${m}_mamo mips $sd >> results/x3/run_infeas_${m}.log 2>&1 &
      NLOPT_SET=x3 $P poc/run_infeas.py $m mipf $sd >> results/x3/run_infeas_${m}.log 2>&1 &
    done; wait
    kill $S; sleep 20
    grep -q "Traceback" results/x3/run_infeas_${m}.log && echo "S2_INFEAS $m: traceback in log $(date)" >> results/queue_log.txt
    [ $(cat results/x3/opt_${m}_mamo_mipsr_s*.jsonl 2>/dev/null | wc -l) -gt 0 ] && break
  done
done
rmdir results/.gpu_claim_$G
echo "S2_INFEAS done $(date)" >> results/queue_log.txt
