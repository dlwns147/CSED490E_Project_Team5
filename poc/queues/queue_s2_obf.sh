#!/bin/bash
# OB-F (docs/prereg/PREREG_HO.md): usage card (freef) and label-free library (formx) on OptiBench, GPU3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export NLOPT_SET=optibench POC_TIMEOUT=7200
mkdir results/.gpu_claim_3 || exit 1
echo "S2_OBF started on GPU3 $(date)" >> results/queue_log.txt
for spec in "Qwen/Qwen3-14B-AWQ q14a" "Qwen/Qwen3-8B q8b" "openai/gpt-oss-20b oss20 low"; do
  set -- $spec; dir=$1 m=$2 lo=$3
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir 8133 3 0.88 obf_$m) || continue
  export POC_BASE_URL=http://127.0.0.1:8133/v1 POC_REASONING_EFFORT=$lo
  for sd in 1 2 3; do
    $P poc/run_nlopt.py ${m}_optibench freef $sd --max_tokens 8192 >> results/x3/run_obf_${m}.log 2>&1 &
    $P poc/run_form.py $m formx $sd >> results/x3/run_obf_${m}.log 2>&1 &
  done; wait
  kill $S; sleep 20; echo "S2_OBF $m done $(date)" >> results/queue_log.txt
done
rmdir results/.gpu_claim_3
echo "S2_OBF done $(date)" >> results/queue_log.txt
