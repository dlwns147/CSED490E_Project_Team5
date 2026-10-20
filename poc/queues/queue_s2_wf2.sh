#!/bin/bash
# WF2 (docs/prereg/PREREG_HO.md): census rule, low-usage-error side. GPU0 gpt-oss-120b (low), GPU1 Qwen3.6 (no thinking).
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
export POC_TIMEOUT=7200
lane() { g=$1 port=$2 dir=$3 m=$4 eff=$5; shift 5
  mkdir results/.gpu_claim_$g || return 1
  S=$(bash poc/start_server.sh /SSD/huggingface/$dir $port $g 0.88 wf2_$m "$@") || { rmdir results/.gpu_claim_$g; return 1; }
  export POC_BASE_URL=http://127.0.0.1:$port/v1 NLOPT_EX_TAG=$m POC_REASONING_EFFORT=$eff
  for sd in 1 2 3; do
    NLOPT_SET=optibench $P poc/run_nlopt.py ${m}_optibench free $sd --max_tokens 8192 >> results/x3/run_wf2_${m}.log 2>&1 &
    NLOPT_SET=optibench $P poc/run_nlopt.py ${m}_optibench freef $sd --max_tokens 8192 >> results/x3/run_wf2_${m}.log 2>&1 &
    NLOPT_SET=optibench $P poc/run_form.py $m formx $sd >> results/x3/run_wf2_${m}.log 2>&1 &
    NLOPT_SET=optmath $P poc/run_nlopt.py ${m}_optmath mip $sd --max_tokens 8192 >> results/x3/run_wf2_${m}.log 2>&1 &
    NLOPT_SET=optmath $P poc/run_form.py $m formx $sd >> results/x3/run_wf2_${m}.log 2>&1 &
    [ -f results/x3/opt_${m}_mip_s1.jsonl ] && NLOPT_SET=optmath $P poc/run_nlopt.py ${m}_optmath mips $sd --max_tokens 8192 >> results/x3/run_wf2_${m}.log 2>&1 &
  done; wait
  kill $S; sleep 20; rmdir results/.gpu_claim_$g; echo "S2_WF2 $m done $(date)" >> results/queue_log.txt; }
echo "S2_WF2 started $(date)" >> results/queue_log.txt
lane 0 8137 openai/gpt-oss-120b oss120 low & sleep 20
lane 1 8138 Qwen/Qwen3.6-35B-A3B-FP8 q36 "" --max-num-seqs 64 --language-model-only & wait
/root/venvs/llm_algo_poc/bin/python - <<'PY' > results/x3/wf2_analysis.log 2>&1
import sys; sys.argv=["x"]; sys.path.insert(0,"poc")
exec(open("poc/analyze_which_fix.py").read().replace('("oss20", "q14a", "q8b", "q32b", "q4b", "q17")', '("oss20", "q14a", "q8b", "q32b", "q4b", "q17", "oss120", "q36")'))
PY
echo "S2_WF2 done $(date)" >> results/queue_log.txt
