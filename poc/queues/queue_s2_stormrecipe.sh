#!/bin/bash
# STORM-RECIPE (docs/prereg/PREREG_X7.md, 2026-10-19): our recipe on top of the trained specialist STORM-Qwen3-4B. Cheap arms = STORM writing
# one OR-Tools program WITHOUT thinking (no-think chat template: empty <think></think>), escalation = its own official TIR samples
# (/SSD/lean_postech/storm/out_*). X3 (NL4OPT + IndustryOR): mip s1 (source of the mined fact) and mipf s1-3; MAMO: mip s1, mipf s1-3, mips s1-3.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
G=1; [ "$(nvidia-smi -i $G --query-gpu=memory.used --format=csv,noheader,nounits)" -lt 2000 ] && mkdir results/.gpu_claim_$G || exit 1
echo "S2_STORMRECIPE started on GPU$G $(date)" >> results/queue_log.txt
o() { mode=$1 sd=$2; shift 2; $P poc/run_nlopt.py $TAG $mode $sd --max_tokens 8192 "$@" >> results/x3/run_${TAG}_${mode}_s$sd.log 2>&1; }
for att in 1 2 3; do
  S=$(bash poc/start_server.sh /SSD/huggingface/tangzhy/STORM-Qwen3-4B 8122 $G 0.85 stormrecipe_$att \
      --chat-template /NAS/SJ/POSTECH/nlp/poc/templates/storm_nothink.jinja --max-model-len 16384) || { sleep 60; continue; }
  export POC_BASE_URL=http://127.0.0.1:8122/v1 NLOPT_EX_TAG=storm
  TAG=storm NLOPT_SET=x3; export NLOPT_SET
  o mip 1 & for sd in 1 2 3; do o mipf $sd & done
  TAG=storm_mamo; NLOPT_SET=mamo; export NLOPT_SET
  o mip 1 & for sd in 1 2 3; do o mipf $sd & done; wait
  for sd in 1 2 3; do o mips $sd & done; wait   # mined fact: STORM's own shortest check-passing X3 program (needs storm mip s1)
  kill $S; sleep 20
  n=$(cat results/x3/opt_storm_mip_s1.jsonl results/x3/opt_storm_mipf_s*.jsonl results/x3/opt_storm_mamo_{mip_s1,mipf_s*,mips_s*}.jsonl 2>/dev/null | wc -l)
  [ "$n" -ge 7420 ] && break
done
rmdir results/.gpu_claim_$G
echo "S2_STORMRECIPE done ($n/7420) $(date)" >> results/queue_log.txt
