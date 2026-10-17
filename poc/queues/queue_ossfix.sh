#!/bin/bash
# Re-run gpt-oss-120b K8 (low / medium) after fixing last_block (54 of 57 "no code" rows in all 79k geometry rows were gpt-oss-120b K8: an extra
# trailing fence broke the pairing; old files kept as *_k8 with the bug, new ones *_k8fix), + 120b high effort K0 / K8. GPU 0.
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python
S=$(poc/start_server.sh /SSD/huggingface/openai/gpt-oss-120b 8065 0 0.88 gptoss120_fix) || { echo "gptoss120_fix failed" >> results/queue_log.txt; exit 1; }
export POC_BASE_URL=http://127.0.0.1:8065/v1
for eff in low medium; do t=oss120${eff:0:3}
  POC_REASONING_EFFORT=$eff $P poc/run_geo_cross.py --model_tag O5_geox${t}_k8fix --stdlib --n_inst 30 --max_tokens 16000 --temperature 0.7 --seed 1 --distract 8 > results/run_O5_geox${t}_k8fix.log 2>&1
done
for k in 0 8; do POC_REASONING_EFFORT=high $P poc/run_geo_cross.py --model_tag O5_geoxoss120hig_k$k --stdlib --n_inst 30 --max_tokens 24000 --temperature 0.7 --seed 1 --distract $k > results/run_O5_geoxoss120hig_k$k.log 2>&1; done
kill $S
echo OSSFIX_DONE >> results/queue_log.txt
