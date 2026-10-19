#!/bin/bash
# CD (docs/prereg/PREREG_CD.md): matched-content code vs description. GPU1; oss20 (low), q14a, q8b; seeds 1-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
mkdir results/.gpu_claim_1 || exit 1
echo "S2_CD started on GPU1 $(date)" >> results/queue_log.txt
for spec in "openai/gpt-oss-20b oss20 low" "Qwen/Qwen3-14B-AWQ q14a" "Qwen/Qwen3-8B q8b"; do
  set -- $spec; dir=$1 m=$2 eff=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir 8130 1 0.88 cd_$m) || continue
  export POC_BASE_URL=http://127.0.0.1:8130/v1 POC_REASONING_EFFORT=$eff NLOPT_EX_TAG=$m
  for sd in 1 2 3; do
    NLOPT_SET=x3 $P poc/run_nlopt.py $m mipt $sd --max_tokens 8192 >> results/x3/run_cd_${m}.log 2>&1 &
    NLOPT_SET=mamo $P poc/run_form.py $m formc $sd >> results/x3/run_cd_${m}.log 2>&1 &
  done; wait
  kill $S; sleep 20; echo "S2_CD $m done $(date)" >> results/queue_log.txt
done
rmdir results/.gpu_claim_1
echo "S2_CD done $(date)" >> results/queue_log.txt
