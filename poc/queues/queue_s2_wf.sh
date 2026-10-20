#!/bin/bash
# WF (docs/prereg/PREREG_HO.md): census rule test. GPU0 Qwen3-4B, GPU1 Qwen3-1.7B, GPU3 Qwen3-32B-AWQ; OptiBench free/freef/formx and
# OptMATH mip/mips/formx, seeds 1-3 (cheap programs only, no thinking).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_TIMEOUT=7200
lane() { g=$1 port=$2 dir=$3 m=$4
  mkdir results/.gpu_claim_$g || return 1
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir $port $g 0.88 wf_$m) || { rmdir results/.gpu_claim_$g; return 1; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1 NLOPT_EX_TAG=$m
  for sd in 1 2 3; do
    NLOPT_SET=optibench $P poc/run_nlopt.py ${m}_optibench free $sd --max_tokens 8192 >> results/x3/run_wf_${m}.log 2>&1 &
    NLOPT_SET=optibench $P poc/run_nlopt.py ${m}_optibench freef $sd --max_tokens 8192 >> results/x3/run_wf_${m}.log 2>&1 &
    NLOPT_SET=optibench $P poc/run_form.py $m formx $sd >> results/x3/run_wf_${m}.log 2>&1 &
    NLOPT_SET=optmath $P poc/run_nlopt.py ${m}_optmath mip $sd --max_tokens 8192 >> results/x3/run_wf_${m}.log 2>&1 &
    NLOPT_SET=optmath $P poc/run_nlopt.py ${m}_optmath mips $sd --max_tokens 8192 >> results/x3/run_wf_${m}.log 2>&1 &
    NLOPT_SET=optmath $P poc/run_form.py $m formx $sd >> results/x3/run_wf_${m}.log 2>&1 &
  done; wait
  kill $S; sleep 20; rmdir results/.gpu_claim_$g; echo "S2_WF $m done $(date)" >> results/queue_log.txt; }
echo "S2_WF started $(date)" >> results/queue_log.txt
lane 0 8134 Qwen/Qwen3-4B q4b & sleep 20; lane 1 8135 Qwen/Qwen3-1.7B q17 & sleep 20; lane 3 8136 Qwen/Qwen3-32B-AWQ q32b & wait
$P poc/analyze_which_fix.py > results/x3/wf_analysis.log 2>&1
echo "S2_WF done $(date)" >> results/queue_log.txt
